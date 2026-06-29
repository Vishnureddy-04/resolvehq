from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import func, and_
from app import db
from models import User, Ticket, TicketEvent
from datetime import datetime, timedelta

bp = Blueprint('analytics', __name__, url_prefix='/api/analytics')

def get_time_filter(days):
    """Get a cutoff datetime for filtering by days"""
    if days == 'all':
        return None
    days_int = int(days) if days.isdigit() else 90
    return datetime.utcnow() - timedelta(days=days_int)

@bp.route('/dashboard', methods=['GET'])
@jwt_required()
def dashboard():
    """Customer or company dashboard metrics"""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    
    if user.role == 'customer':
        # Customer dashboard
        tickets = Ticket.query.filter_by(created_by=user.id).all()
        total = len(tickets)
        open_count = len([t for t in tickets if t.status in ['submitted', 'in_review', 'in_progress']])
        pending = len([t for t in tickets if t.status == 'awaiting_customer'])
        closed = len([t for t in tickets if t.status in ['resolved', 'closed']])
        
        # Avg resolution time
        resolved = [t for t in tickets if t.resolved_at or t.closed_at]
        avg_resolution = None
        if resolved:
            times = [(t.closed_at or t.resolved_at - t.created_at).total_seconds() / 3600 for t in resolved]
            avg_resolution = sum(times) / len(times)
        
        # Recent activity
        recent = sorted(tickets, key=lambda t: t.updated_at, reverse=True)[:5]
        
        return jsonify({
            'total': total,
            'open': open_count,
            'pending': pending,
            'closed': closed,
            'avg_resolution_hours': avg_resolution,
            'recent': [t.to_dict(include_events=False) for t in recent],
        }), 200
    
    elif user.role == 'company':
        # Company dashboard
        tickets = Ticket.query.all()
        total = len(tickets)
        open_count = len([t for t in tickets if t.status in ['submitted', 'in_review', 'in_progress']])
        pending = len([t for t in tickets if t.status == 'awaiting_customer'])
        p0_active = len([t for t in tickets if t.priority == 'P0' and t.status not in ['resolved', 'closed']])
        closed = len([t for t in tickets if t.status in ['resolved', 'closed']])
        
        # Unassigned
        unassigned = [t for t in tickets if not t.assigned_team and t.status not in ['resolved', 'closed']]
        
        # Recent activity
        recent = sorted(tickets, key=lambda t: t.updated_at, reverse=True)[:8]
        
        return jsonify({
            'total': total,
            'open': open_count,
            'pending': pending,
            'p0_active': p0_active,
            'closed': closed,
            'unassigned_count': len(unassigned),
            'recent': [t.to_dict(include_events=False) for t in recent],
        }), 200
    
    return jsonify({'error': 'Invalid role'}), 403

@bp.route('/metrics', methods=['GET'])
@jwt_required()
def metrics():
    """Detailed metrics for company dashboard"""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    
    if not user or user.role != 'company':
        return jsonify({'error': 'Only company users can access metrics'}), 403
    
    days = request.args.get('days', '90')
    cutoff = get_time_filter(days)
    
    query = Ticket.query
    if cutoff:
        query = query.filter(Ticket.created_at >= cutoff)
    
    tickets = query.all()
    
    # Group by type
    types = {}
    for ticket in tickets:
        t = ticket.issue_type
        types[t] = types.get(t, 0) + 1
    
    # Group by category
    categories = {}
    for ticket in tickets:
        c = ticket.category
        categories[c] = categories.get(c, 0) + 1
    
    # Group by priority
    priorities = {}
    for ticket in tickets:
        p = ticket.priority or 'Unset'
        priorities[p] = priorities.get(p, 0) + 1
    
    # Group by customer
    customers = {}
    for ticket in tickets:
        c = ticket.customer_company
        customers[c] = customers.get(c, 0) + 1
    
    # TAT metrics
    first_response_times = []
    resolution_times = []
    for ticket in tickets:
        # First response
        event = next((e for e in ticket.events if e.stage != 'submitted'), None)
        if event:
            first_response_times.append((event.created_at - ticket.created_at).total_seconds() / 3600)
        
        # Resolution
        if ticket.closed_at or ticket.resolved_at:
            resolution_times.append((ticket.closed_at or ticket.resolved_at - ticket.created_at).total_seconds() / 3600)
    
    avg_first_response = sum(first_response_times) / len(first_response_times) if first_response_times else None
    avg_resolution = sum(resolution_times) / len(resolution_times) if resolution_times else None
    closure_rate = (len([t for t in tickets if t.status in ['resolved', 'closed']]) / len(tickets) * 100) if tickets else 0
    
    return jsonify({
        'range_days': days,
        'total_tickets': len(tickets),
        'by_type': types,
        'by_category': categories,
        'by_priority': priorities,
        'by_customer': customers,
        'tat_first_response_hours': avg_first_response,
        'tat_resolution_hours': avg_resolution,
        'closure_rate_percent': round(closure_rate, 1),
    }), 200

@bp.route('/team-workload', methods=['GET'])
@jwt_required()
def team_workload():
    """Company view: open tickets assigned to each team"""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    
    if not user or user.role != 'company':
        return jsonify({'error': 'Only company users can access this'}), 403
    
    # Count open tickets by team
    tickets = Ticket.query.filter(
        Ticket.assigned_team != None,
        Ticket.status.notin_(['resolved', 'closed'])
    ).all()
    
    workload = {}
    for ticket in tickets:
        team = ticket.assigned_team
        workload[team] = workload.get(team, 0) + 1
    
    return jsonify(workload), 200

@bp.route('/recurring', methods=['GET'])
@jwt_required()
def recurring_issues():
    """Detect recurring/similar issues in last 90 days"""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    
    if not user or user.role != 'company':
        return jsonify({'error': 'Only company users can access this'}), 403
    
    cutoff = datetime.utcnow() - timedelta(days=90)
    tickets = Ticket.query.filter(Ticket.created_at >= cutoff).all()
    
    # Simple keyword clustering
    stop_words = {'the', 'and', 'for', 'are', 'was', 'with', 'is', 'it', 'a', 'an', 'on', 'in', 'of', 'to'}
    
    def tokenize(title):
        words = title.lower().replace('-', ' ').split()
        return [w for w in words if len(w) > 3 and w not in stop_words]
    
    def similarity(tokens1, tokens2):
        if not tokens1 or not tokens2:
            return 0
        common = len(set(tokens1) & set(tokens2))
        total = len(set(tokens1) | set(tokens2))
        return common / total if total > 0 else 0
    
    # Cluster tickets
    clusters = []
    for ticket in tickets:
        tokens = tokenize(ticket.title)
        placed = False
        for cluster in clusters:
            if any(similarity(tokens, tokenize(t.title)) > 0.4 for t in cluster):
                cluster.append(ticket)
                placed = True
                break
        if not placed:
            clusters.append([ticket])
    
    # Return clusters with 2+ tickets
    recurring = []
    for cluster in clusters:
        if len(cluster) >= 2:
            latest = sorted(cluster, key=lambda t: t.created_at, reverse=True)[0]
            recurring.append({
                'title': latest.title,
                'count': len(cluster),
                'tickets': [t.ticket_id for t in cluster],
                'companies': list(set(t.customer_company for t in cluster)),
            })
    
    return jsonify(sorted(recurring, key=lambda x: x['count'], reverse=True)), 200

@bp.route('/customer/<customer_company>', methods=['GET'])
@jwt_required()
def customer_analytics(customer_company):
    """Company view: analytics for a specific customer"""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    
    if not user or user.role != 'company':
        return jsonify({'error': 'Only company users can access this'}), 403
    
    tickets = Ticket.query.filter_by(customer_company=customer_company).all()
    
    if not tickets:
        return jsonify({'error': 'No tickets found for this customer'}), 404
    
    total = len(tickets)
    open_count = len([t for t in tickets if t.status not in ['resolved', 'closed']])
    closed = len([t for t in tickets if t.status in ['resolved', 'closed']])
    
    # Resolution time
    resolved = [t for t in tickets if t.closed_at or t.resolved_at]
    avg_res = None
    if resolved:
        times = [(t.closed_at or t.resolved_at - t.created_at).total_seconds() / 3600 for t in resolved]
        avg_res = sum(times) / len(times)
    
    return jsonify({
        'customer': customer_company,
        'total_tickets': total,
        'open': open_count,
        'closed': closed,
        'avg_resolution_hours': avg_res,
        'tickets': [t.to_dict(include_events=False) for t in sorted(tickets, key=lambda x: x.updated_at, reverse=True)],
    }), 200
