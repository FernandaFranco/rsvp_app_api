# backend/services/email_service.py
import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail


def send_rsvp_notification(event, attendee):
    """Send email to host when someone RSVPs"""

    sender_email = "ferfrancodias@gmail.com"

    message = Mail(
        from_email=sender_email,
        to_emails=event.host.email,
        subject=f"Novo RSVP para {event.title}",
        html_content=f"""
            <h2>Nova Confirmação de Presença!</h2>
            <p><strong>{attendee.name}</strong> confirmou presença no seu evento: <strong>{event.title}</strong></p>
            
            <h3>Detalhes:</h3>
            <ul>
                <li>Adultos: {attendee.num_adults}</li>
                <li>Crianças: {attendee.num_children}</li>
                <li>WhatsApp: {attendee.whatsapp_number}</li>
                {f'<li>Comentários: {attendee.comments}</li>' if attendee.comments else ''}
            </ul>
            
            <p>Veja todos os convidados no seu painel.</p>
        """,
    )

    try:
        sg = SendGridAPIClient(os.getenv("SENDGRID_API_KEY"))
        response = sg.send(message)
        print(f"✅ Email enviado! Status: {response.status_code}")
        return True
    except Exception as e:
        print(f"❌ Erro ao enviar email: {e}")
        return False


def send_modification_notification(event, attendee, changes):
    """Send email to host when someone modifies their RSVP"""

    sender_email = "ferfrancodias@gmail.com"

    message = Mail(
        from_email=sender_email,
        to_emails=event.host.email,
        subject=f"RSVP Modificado - {event.title}",
        html_content=f"""
            <h2>RSVP Modificado</h2>
            <p><strong>{attendee.name}</strong> modificou a confirmação para: <strong>{event.title}</strong></p>
            
            <h3>Detalhes Atualizados:</h3>
            <ul>
                <li>Adultos: {attendee.num_adults}</li>
                <li>Crianças: {attendee.num_children}</li>
                <li>Comentários: {attendee.comments}</li>
            </ul>
        """,
    )

    try:
        sg = SendGridAPIClient(os.getenv("SENDGRID_API_KEY"))
        sg.send(message)
        print("✅ Email de modificação enviado!")
        return True
    except Exception as e:
        print(f"❌ Erro ao enviar email: {e}")
        return False


def send_cancellation_notification(event, attendee, reason=""):
    """Send email to host when someone cancels"""

    sender_email = "ferfrancodias@gmail.com"

    message = Mail(
        from_email=sender_email,
        to_emails=event.host.email,
        subject=f"RSVP Cancelado - {event.title}",
        html_content=f"""
            <h2>RSVP Cancelado</h2>
            <p><strong>{attendee.name}</strong> cancelou a presença em: <strong>{event.title}</strong></p>
            
            {f'<p><strong>Motivo:</strong> {reason}</p>' if reason else ''}
        """,
    )

    try:
        sg = SendGridAPIClient(os.getenv("SENDGRID_API_KEY"))
        sg.send(message)
        print("✅ Email de cancelamento enviado!")
        return True
    except Exception as e:
        print(f"❌ Erro ao enviar email: {e}")
        return False
