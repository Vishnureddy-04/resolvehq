from app import db
from models import User, Ticket, TicketEvent
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash

def seed_demo_data():
    """Populate database with demo users and tickets"""
    
    NOW = datetime.utcnow()
    H = timedelta(hours=1)
    D = timedelta(days=1)
    
    # ---- USERS ----
    # Customers
    customer1 = User(
        email='customer@acme.com',
        password_hash=generate_password_hash('demo1234'),
        name='Alex Carter',
        role='customer',
        company='Acme Inc.',
        customer_name='Priya Mehta'
    )
    customer2 = User(
        email='raj@techflow.com',
        password_hash=generate_password_hash('demo1234'),
        name='Raj Patel',
        role='customer',
        company='TechFlow Ltd',
        customer_name='Raj Patel'
    )
    customer3 = User(
        email='chen@globex.com',
        password_hash=generate_password_hash('demo1234'),
        name='Chen Wei',
        role='customer',
        company='Globex Corp',
        customer_name='Chen Wei'
    )
    
    # Company / Agents
    agent1 = User(
        email='agent@resolvehq.com',
        password_hash=generate_password_hash('demo1234'),
        name='Jamie Doyle',
        role='company',
        company='ResolveHQ',
        team='Engineering'
    )
    agent2 = User(
        email='impl@resolvehq.com',
        password_hash=generate_password_hash('demo1234'),
        name='Sarah Chen',
        role='company',
        company='ResolveHQ',
        team='Implementation'
    )
    
    db.session.add_all([customer1, customer2, customer3, agent1, agent2])
    db.session.flush()  # get IDs
    
    # ---- TICKETS ----
    tickets = [
        {
            'ticket_id': 'TKT-3001',
            'title': 'Checkout page 500 on Visa card payment',
            'desc': 'When a customer tries to pay with a Visa card on the hosted checkout, the page returns a 500 error after clicking Pay. Reproducible in production. Stripe test mode works fine.',
            'category': 'Product bug',
            'type': 'bug',
            'priority': 'P0',
            'status': 'in_progress',
            'customer_name': 'Priya Mehta',
            'customer_email': 'customer@acme.com',
            'customer_company': 'Acme Inc.',
            'created_by': customer1.id,
            'assigned_to': agent1.id,
            'assigned_team': 'Engineering',
            'created_at': NOW - 2*D,
            'updated_at': NOW - 1*D,
            'events': [
                ('submitted', NOW - 2*D, 'Issue submitted by customer'),
                ('in_review', NOW - 2*D + 2*H, 'Triaged as P0 — payment-blocking. Escalated immediately.'),
                ('in_progress', NOW - 1*D, 'Assigned to Payments squad. Investigating gateway logs.'),
            ]
        },
        {
            'ticket_id': 'TKT-3002',
            'title': 'Okta SSO redirect loop for new hires',
            'desc': 'New employees added this week get stuck in a redirect loop when signing in via Okta SSO. Existing users are fine.',
            'category': 'Account & access',
            'type': 'bug',
            'priority': 'P1',
            'status': 'awaiting_customer',
            'customer_name': 'Raj Patel',
            'customer_email': 'raj@techflow.com',
            'customer_company': 'TechFlow Ltd',
            'created_by': customer2.id,
            'assigned_to': agent2.id,
            'assigned_team': 'Implementation',
            'created_at': NOW - 3*D,
            'updated_at': NOW - 18*H,
            'events': [
                ('submitted', NOW - 3*D, 'Issue submitted by customer'),
                ('in_review', NOW - 3*D + 5*H, 'Reproduced on staging env.'),
                ('awaiting_customer', NOW - 18*H, 'Could you share the Okta group the new staff are assigned to? Need this to investigate further.', True),
            ]
        },
        {
            'ticket_id': 'TKT-3003',
            'title': 'Bulk CSV import for contacts',
            'desc': 'It would help to import contacts in bulk from a CSV rather than one by one during onboarding.',
            'category': 'Feature request',
            'type': 'enhancement',
            'priority': 'P3',
            'status': 'in_review',
            'customer_name': 'Chen Wei',
            'customer_email': 'chen@globex.com',
            'customer_company': 'Globex Corp',
            'created_by': customer3.id,
            'assigned_to': None,
            'assigned_team': None,
            'created_at': NOW - 5*D,
            'updated_at': NOW - 4*D,
            'events': [
                ('submitted', NOW - 5*D, 'Issue submitted by customer'),
                ('in_review', NOW - 4*D, 'Logged for Q3 roadmap review. PM notified.'),
            ]
        },
        {
            'ticket_id': 'TKT-3004',
            'title': 'Invoice PDF shows wrong EU tax total',
            'desc': 'Downloaded invoice PDF lists a tax amount that does not match the dashboard figure for EU customers.',
            'category': 'Billing',
            'type': 'bug',
            'priority': None,
            'status': 'submitted',
            'customer_name': 'Sara Lund',
            'customer_email': 'sara@nordretail.no',
            'customer_company': 'NordRetail AS',
            'created_by': customer1.id,
            'assigned_to': None,
            'assigned_team': None,
            'created_at': NOW - 6*H,
            'updated_at': NOW - 6*H,
            'events': [
                ('submitted', NOW - 6*H, 'Issue submitted by customer'),
            ]
        },
        {
            'ticket_id': 'TKT-3005',
            'title': 'Analytics charts blank on Safari 17',
            'desc': 'Dashboard charts render blank on Safari 17. Chrome and Firefox are fine.',
            'category': 'Product bug',
            'type': 'bug',
            'priority': 'P2',
            'status': 'resolved',
            'customer_name': 'Priya Mehta',
            'customer_email': 'customer@acme.com',
            'customer_company': 'Acme Inc.',
            'created_by': customer1.id,
            'assigned_to': agent1.id,
            'assigned_team': 'Engineering',
            'created_at': NOW - 9*D,
            'updated_at': NOW - 6*D,
            'resolved_at': NOW - 6*D,
            'events': [
                ('submitted', NOW - 9*D, 'Issue submitted by customer'),
                ('in_review', NOW - 9*D + 4*H, 'Reproduced. Root cause: unsupported CSS mask.'),
                ('in_progress', NOW - 8*D, 'Fix in progress.'),
                ('resolved', NOW - 6*D, 'Patched in release 4.2.1. Please confirm on your end.', True),
            ]
        },
        {
            'ticket_id': 'TKT-3006',
            'title': 'Amex card payment failing at checkout',
            'desc': 'Similar to the earlier card payment 500 — now Amex cards fail at the Pay step while Visa works.',
            'category': 'Product bug',
            'type': 'bug',
            'priority': 'P1',
            'status': 'closed',
            'customer_name': 'Chen Wei',
            'customer_email': 'chen@globex.com',
            'customer_company': 'Globex Corp',
            'created_by': customer3.id,
            'assigned_to': agent1.id,
            'assigned_team': 'Engineering',
            'created_at': NOW - 35*D,
            'updated_at': NOW - 30*D,
            'resolved_at': NOW - 31*D,
            'closed_at': NOW - 30*D,
            'events': [
                ('submitted', NOW - 35*D, 'Issue submitted by customer'),
                ('in_review', NOW - 35*D + 2*H, 'Repeat of gateway issue.'),
                ('in_progress', NOW - 34*D, 'Work in progress.'),
                ('resolved', NOW - 31*D, 'Gateway routing fixed for Amex.', True),
                ('closed', NOW - 30*D, 'Confirmed working.'),
            ]
        },
    ]
    
    # Create tickets and events
    for t in tickets:
        events = t.pop('events', [])
        ticket = Ticket(**t)
        db.session.add(ticket)
        db.session.flush()
        
        for event in events:
            stage, created_at, note = event[0], event[1], event[2]
            is_reply = event[3] if len(event) > 3 else False
            evt = TicketEvent(
                ticket_id=ticket.id,
                stage=stage,
                note=note,
                is_reply=is_reply,
                created_at=created_at
            )
            db.session.add(evt)
    
    db.session.commit()
    print("✓ Demo data seeded successfully")
