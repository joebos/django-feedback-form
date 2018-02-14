"""Forms for the ``feedback_form`` app."""
from django import forms
from django.conf import settings
from django.core.urlresolvers import reverse

#from django_libs.utils_email import send_email

from .models import Feedback
from django.template.loader import render_to_string
from django.template import TemplateDoesNotExist
from django.core.mail import EmailMultiAlternatives, EmailMessage
from django.core.mail import get_connection


class FeedbackForm(forms.ModelForm):
    """
    A feedback form with modern spam protection.

    :url: Field to trap spam bots.

    """
    url = forms.URLField(required=False)

    def __init__(self, user=None, url=None, prefix='feedback',
                 content_object=None, *args, **kwargs):
        self.content_object = content_object
        super(FeedbackForm, self).__init__(prefix='feedback', *args, **kwargs)
        if url:
            self.instance.current_url = url
        if user:
            self.instance.user = user
            del self.fields['email']
            self.instance.email = str(user.email) if hasattr(user, "email") else settings.FROM_EMAIL
        else:
            self.fields['email'].required = True

    def save(self):
        if not self.cleaned_data.get('url'):
            self.instance.content_object = self.content_object

            obj = super(FeedbackForm, self).save()
            context = {
                'url': reverse('admin:feedback_form_feedback_change',
                               args=(obj.id, )),
                'feedback': obj,
            }
            self.send_mail(

                'feedback_form/email/subject.html',
                'feedback_form/email/body.html',
                self.instance.email,
                [support[1] for support in settings.SUPPORT],
                [],
                context
            )
            return obj

    class Media:
        css = {'all': ('feedback_form/css/feedback_form.css'), }
        js = ('feedback_form/js/feedback_form.js', )

    class Meta:
        model = Feedback
        fields = ('email', 'message')

    def render_mail_with_template(self, subject_template, body_template, from_email, tos, bccs, context):
        """
        Renders an e-mail to `email`.  `template_prefix` identifies the
        e-mail that is to be sent, e.g. "account/email/email_confirmation"
        """
        subject = render_to_string(subject_template, context)
        # remove superfluous line breaks
        subject = " ".join(subject.splitlines()).strip()
        #subject = self.format_email_subject(subject)

        bodies = {}
        for ext in ['html', 'txt']:
            try:
                template_name = body_template
                bodies[ext] = render_to_string(template_name, context).strip()
            except TemplateDoesNotExist:
                if ext == 'txt' and not bodies:
                    # We need at least one body
                    raise
        if 'txt' in bodies:
            msg = EmailMultiAlternatives(subject,
                                         bodies['txt'],
                                         from_email=from_email,
                                         to=tos,
                                         bcc=bccs)
            if 'html' in bodies:
                msg.attach_alternative(bodies['html'], 'text/html')
        else:
            msg = EmailMessage( subject,
                                bodies['html'],
                                from_email=from_email,
                                to=tos,
                                bcc=bccs)
            msg.content_subtype = 'html'  # Main content is now text/html
        return msg

    def send_mail(self, subject_template, body_template, from_email, tos, bccs, context):
        msg = self.render_mail_with_template(subject_template, body_template, from_email, tos, bccs, context)

        msg.connection = get_connection('django.core.mail.backends.smtp.EmailBackend')
        msg.send()
        msg.connection.close()

