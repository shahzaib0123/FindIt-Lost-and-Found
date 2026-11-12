"""Routes for the messaging blueprint."""
from datetime import datetime, timezone
from flask import abort, flash, redirect, render_template, url_for
from flask_login import current_user, login_required
from app.extensions import db
from app.models.communication import (
    Conversation,
    ConversationParticipant,
    Message,
    Notification,
)
from app.models.reporting import ItemReport
from . import messaging_bp
from .forms import MessageForm


@messaging_bp.route('/', methods=['GET'])
@login_required
def index():
    """List all conversations the current user participates in."""
    conversations = (
        Conversation.query.join(ConversationParticipant)
        .filter(ConversationParticipant.user_id == current_user.id)
        .order_by(Conversation.updated_at.desc())
        .all()
    )
    unread_count = Notification.query.filter_by(user_id=current_user.id, is_read=False).count()
    return render_template(
        'messaging/conversations.html',
        conversations=conversations,
        unread_count=unread_count,
    )


@messaging_bp.route('/<int:id>', methods=['GET', 'POST'])
@login_required
def conversation(id):
    """View a conversation thread and send new messages."""
    conv = db.get_or_404(Conversation, id)
    participant = ConversationParticipant.query.filter_by(
        conversation_id=conv.id,
        user_id=current_user.id,
    ).first()
    if participant is None:
        abort(403)

    form = MessageForm()
    if form.validate_on_submit():
        msg = Message(
            conversation_id=conv.id,
            sender_id=current_user.id,
            message_text=form.message_text.data.strip(),
        )
        conv.updated_at = datetime.now(timezone.utc)
        db.session.add(msg)

        for other in conv.participants:
            if other.user_id != current_user.id:
                db.session.add(
                    Notification(
                        user_id=other.user_id,
                        title='New Message',
                        message=f'{current_user.username} sent you a message.',
                        notification_type='info',
                    )
                )

        db.session.commit()
        flash('Message sent.', 'success')
        return redirect(url_for('messaging.conversation', id=conv.id))

    unread_messages = Message.query.filter(
        Message.conversation_id == conv.id,
        Message.sender_id != current_user.id,
        Message.is_read.is_(False),
    ).all()
    if unread_messages:
        for m in unread_messages:
            m.is_read = True
        db.session.commit()

    return render_template('messaging/conversation.html', conversation=conv, form=form)


@messaging_bp.route('/start/<int:report_id>', methods=['POST'])
@login_required
def start(report_id):
    """Start or resume a conversation with the owner of an item report."""
    report = db.get_or_404(ItemReport, report_id)
    if report.user_id == current_user.id:
        flash('You cannot start a conversation with yourself.', 'warning')
        return redirect(url_for('items.detail', id=report.id))

    existing_convs = (
        Conversation.query.join(ConversationParticipant)
        .filter(
            Conversation.report_id == report.id,
            ConversationParticipant.user_id == current_user.id,
        )
        .all()
    )
    for conv in existing_convs:
        participant_ids = {p.user_id for p in conv.participants}
        if report.user_id in participant_ids:
            return redirect(url_for('messaging.conversation', id=conv.id))

    conv = Conversation(report_id=report.id)
    db.session.add(conv)
    db.session.flush()

    db.session.add(ConversationParticipant(conversation_id=conv.id, user_id=current_user.id))
    db.session.add(ConversationParticipant(conversation_id=conv.id, user_id=report.user_id))
    db.session.commit()

    flash('Conversation started.', 'success')
    return redirect(url_for('messaging.conversation', id=conv.id))


@messaging_bp.route('/notifications', methods=['GET'])
@login_required
def notifications():
    """List all notifications for the current user."""
    user_notifications = (
        Notification.query.filter_by(user_id=current_user.id)
        .order_by(Notification.created_at.desc())
        .all()
    )
    return render_template('messaging/notifications.html', notifications=user_notifications)


@messaging_bp.route('/notifications/<int:id>/read', methods=['POST'])
@login_required
def mark_notification_read(id):
    """Mark a notification as read."""
    notification = db.get_or_404(Notification, id)
    if notification.user_id != current_user.id:
        abort(403)

    notification.is_read = True
    db.session.commit()
    flash('Notification marked as read.', 'info')
    return redirect(url_for('messaging.notifications'))
