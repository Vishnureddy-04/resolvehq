from database import db
from datetime import datetime
import json

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    name = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(50), nullable=False)  # 'customer', 'company'
    company = db.Column(db.String(255))  # for customers: their company; for agents: the company they work for
    customer_name = db.Column(db.String(255))  # for customers: their display name
    team = db.Column(db.String(100))  # for company users: Engineering, Implementation, etc.
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    tickets = db.relationship('Ticket', backref='created_by_user', foreign_keys='Ticket.created_by')
    assigned_tickets = db.relationship('Ticket', backref='assigned_to_user', foreign_keys='Ticket.assigned_to')
    
    def to_dict(self):
        return {
            'id': self.id,
            'email': self.email,
            'name': self.name,
            'role': self.role,
            'company': self.company,
            'customer_name': self.customer_name,
            'team': self.team,
        }

class Ticket(db.Model):
    __tablename__ = 'tickets'
    
    id = db.Column(db.Integer, primary_key=True)
    ticket_id = db.Column(db.String(50), unique=True, nullable=False, index=True)  # TKT-xxxx
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(100), nullable=False)
    issue_type = db.Column(db.String(50), nullable=False)  # bug, enhancement, support
    priority = db.Column(db.String(10))  # P0, P1, P2, P3, null = unset
    status = db.Column(db.String(50), default='submitted')  # submitted, in_review, in_progress, awaiting_customer, resolved, closed
    
    # WHO
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)  # customer who submitted
    assigned_to = db.Column(db.Integer, db.ForeignKey('users.id'))  # agent/team member
    assigned_team = db.Column(db.String(100))  # Engineering, Implementation, etc.
    
    # CUSTOMER INFO
    customer_name = db.Column(db.String(255), nullable=False)
    customer_email = db.Column(db.String(255), nullable=False)
    customer_company = db.Column(db.String(255), nullable=False)
    
    # TIMESTAMPS
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, index=True)
    resolved_at = db.Column(db.DateTime)
    closed_at = db.Column(db.DateTime)
    
    # SCREENSHOT
    screenshot_url = db.Column(db.String(500))
    
    # EVENTS
    events = db.relationship('TicketEvent', backref='ticket', cascade='all, delete-orphan', lazy=True)
    
    def to_dict(self, include_events=True):
        d = {
            'id': self.ticket_id,
            'title': self.title,
            'desc': self.description,
            'category': self.category,
            'type': self.issue_type,
            'priority': self.priority,
            'status': self.status,
            'customer': self.customer_name,
            'company': self.customer_company,
            'team': self.assigned_team,
            'createdAt': int(self.created_at.timestamp() * 1000) if self.created_at else None,
            'updatedAt': int(self.updated_at.timestamp() * 1000) if self.updated_at else None,
            'resolvedAt': int(self.resolved_at.timestamp() * 1000) if self.resolved_at else None,
            'closedAt': int(self.closed_at.timestamp() * 1000) if self.closed_at else None,
            'shot': self.screenshot_url,
        }
        if include_events:
            d['events'] = [e.to_dict() for e in sorted(self.events, key=lambda x: x.created_at)]
        return d

class TicketEvent(db.Model):
    __tablename__ = 'ticket_events'
    
    id = db.Column(db.Integer, primary_key=True)
    ticket_id = db.Column(db.Integer, db.ForeignKey('tickets.id'), nullable=False, index=True)
    stage = db.Column(db.String(50), nullable=False)  # submitted, in_review, in_progress, awaiting_customer, resolved, closed
    note = db.Column(db.Text)
    is_reply = db.Column(db.Boolean, default=False)  # whether this is a message to the customer
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    def to_dict(self):
        return {
            'stage': self.stage,
            'at': int(self.created_at.timestamp() * 1000),
            'note': self.note or '',
            'isReply': self.is_reply,
        }
