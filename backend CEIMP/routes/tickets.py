from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import or_, and_
from app import db
from models import User, Ticket, TicketEvent
from datetime import datetime

bp = Blueprint('tickets', __name__, url_prefix='/api/tickets')

@bp.route('', methods=['POST'])
@jwt_required()
def create_ticket():
    """Customer creates a new ticket"""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    
    if not user or user.role != 'customer':
        return jsonify({'error': 'Only customers can create tickets'}), 403
    
    data = request.get_json()
    
    # Validate
    required = ['title', 'description', 'category', 'type']
    if not all(data.get(f) for f in required):
        return jsonify({'error': 'Missing required fields: ' + ', '.join(required)}), 400
    
    # Generate ticket ID
    last_ticket = Ticket.query.order_by(Ticket.id.desc()).first()
    next_num = (last_ticket.id + 1) if last_ticket else 3001
    ticket_id = f'TKT-{next_num}'
    
    # Create ticket
    ticket = Ticket(
        ticket_id=ticket_id,
        title=data['title'],
        description=data['description'],
        category=data['category'],
        issue_type=data['type'],
        priority=None,  # Company sets this during triage
        status='submitted',
        created_by=user.id,
        customer_name=user.customer_name or user.name,
        customer_email=user.email,
        customer_company=user.company,
        screenshot_url=data.get('screenshot_url'),  # base64 or URL
    )
    db.session.add(ticket)
    db.session.flush()
    
    # Create initial event
    event = TicketEvent(
        ticket_id=ticket.id,
        stage='submitted',
        note='Issue submitted by customer',
    )
    db.session.add(event)
    db.session.commit()
    
    return jsonify(ticket.to_dict()), 201

@bp.route('/<ticket_id>', methods=['GET'])
@jwt_required()
def get_ticket(ticket_id):
    """Get a single ticket by ID"""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    
    ticket = Ticket.query.filter_by(ticket_id=ticket_id).first()
    if not ticket:
        return jsonify({'error': 'Ticket not found'}), 404
    
    # Authorization: customer can only see their own, company can see all
    if user.role == 'customer' and ticket.created_by != user.id:
        return jsonify({'error': 'Not authorized'}), 403
    
    return jsonify(ticket.to_dict()), 200

@bp.route('', methods=['GET'])
@jwt_required()
def list_tickets():
    """List tickets based on user role and filters"""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    
    filter_status = request.args.get('status')
    filter_priority = request.args.get('priority')
    filter_team = request.args.get('team')
    filter_customer = request.args.get('customer')
    sort_by = request.args.get('sort', 'updated')  # 'updated' or 'created'
    
    query = Ticket.query
    
    # Authorization
    if user.role == 'customer':
        # Customers only see their own tickets
        query = query.filter_by(created_by=user.id)
    elif user.role == 'company':
        # Company sees all tickets (no filter)
        pass
    else:
        return jsonify({'error': 'Invalid user role'}), 403
    
    # Apply filters
    if filter_status:
        query = query.filter_by(status=filter_status)
    if filter_priority and user.role == 'company':
        query = query.filter_by(priority=filter_priority)
    if filter_team and user.role == 'company':
        query = query.filter_by(assigned_team=filter_team)
    if filter_customer and user.role == 'company':
        query = query.filter_by(customer_company=filter_customer)
    
    # Sort
    if sort_by == 'created':
        query = query.order_by(Ticket.created_at.desc())
    else:
        query = query.order_by(Ticket.updated_at.desc())
    
    tickets = query.all()
    return jsonify([t.to_dict(include_events=False) for t in tickets]), 200

@bp.route('/<ticket_id>', methods=['PATCH'])
@jwt_required()
def update_ticket(ticket_id):
    """Company updates ticket (priority, category, type, team, status)"""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    
    if not user or user.role != 'company':
        return jsonify({'error': 'Only company agents can update tickets'}), 403
    
    ticket = Ticket.query.filter_by(ticket_id=ticket_id).first()
    if not ticket:
        return jsonify({'error': 'Ticket not found'}), 404
    
    data = request.get_json()
    
    # Update fields
    if 'priority' in data:
        ticket.priority = data['priority']
    if 'category' in data:
        ticket.category = data['category']
    if 'type' in data:
        ticket.issue_type = data['type']
    if 'assigned_team' in data:
        ticket.assigned_team = data['assigned_team']
        ticket.assigned_to = user.id
    
    # Handle status changes
    if 'status' in data and data['status'] != ticket.status:
        old_status = ticket.status
        new_status = data['status']
        ticket.status = new_status
        
        # Add status change event
        event = TicketEvent(
            ticket_id=ticket.id,
            stage=new_status,
            note=f'Status changed from {old_status} to {new_status}',
        )
        db.session.add(event)
        
        # Update timestamp fields
        if new_status == 'resolved':
            ticket.resolved_at = datetime.utcnow()
        if new_status == 'closed':
            ticket.closed_at = datetime.utcnow()
    
    ticket.updated_at = datetime.utcnow()
    db.session.commit()
    
    return jsonify(ticket.to_dict()), 200

@bp.route('/<ticket_id>/reply', methods=['POST'])
@jwt_required()
def send_reply(ticket_id):
    """Company sends a message/reply to customer on a ticket"""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    
    if not user or user.role != 'company':
        return jsonify({'error': 'Only company agents can send replies'}), 403
    
    ticket = Ticket.query.filter_by(ticket_id=ticket_id).first()
    if not ticket:
        return jsonify({'error': 'Ticket not found'}), 404
    
    data = request.get_json()
    
    if not data.get('message'):
        return jsonify({'error': 'Message is required'}), 400
    
    # Create reply event
    event = TicketEvent(
        ticket_id=ticket.id,
        stage=ticket.status,  # keep current stage
        note=data['message'],
        is_reply=True,
    )
    db.session.add(event)
    
    # Optionally update status if specified
    if 'status' in data and data['status'] != ticket.status:
        ticket.status = data['status']
        if data['status'] == 'resolved':
            ticket.resolved_at = datetime.utcnow()
        if data['status'] == 'closed':
            ticket.closed_at = datetime.utcnow()
    
    ticket.updated_at = datetime.utcnow()
    db.session.commit()
    
    return jsonify({
        'message': 'Reply sent',
        'ticket': ticket.to_dict(),
    }), 200

@bp.route('/<ticket_id>/resolve', methods=['POST'])
@jwt_required()
def mark_resolved(ticket_id):
    """Company marks ticket as resolved"""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    
    if not user or user.role != 'company':
        return jsonify({'error': 'Only company agents can resolve tickets'}), 403
    
    ticket = Ticket.query.filter_by(ticket_id=ticket_id).first()
    if not ticket:
        return jsonify({'error': 'Ticket not found'}), 404
    
    data = request.get_json()
    message = data.get('message', 'Issue has been resolved.')
    
    # Update status
    ticket.status = 'resolved'
    ticket.resolved_at = datetime.utcnow()
    ticket.updated_at = datetime.utcnow()
    
    # Add event
    event = TicketEvent(
        ticket_id=ticket.id,
        stage='resolved',
        note=message,
        is_reply=True,
    )
    db.session.add(event)
    db.session.commit()
    
    return jsonify(ticket.to_dict()), 200

@bp.route('/<ticket_id>/close', methods=['POST'])
@jwt_required()
def close_ticket(ticket_id):
    """Company closes a resolved ticket"""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    
    if not user or user.role != 'company':
        return jsonify({'error': 'Only company agents can close tickets'}), 403
    
    ticket = Ticket.query.filter_by(ticket_id=ticket_id).first()
    if not ticket:
        return jsonify({'error': 'Ticket not found'}), 404
    
    ticket.status = 'closed'
    ticket.closed_at = datetime.utcnow()
    ticket.updated_at = datetime.utcnow()
    
    event = TicketEvent(
        ticket_id=ticket.id,
        stage='closed',
        note='Ticket closed. Customer confirmed resolution.',
    )
    db.session.add(event)
    db.session.commit()
    
    return jsonify(ticket.to_dict()), 200
