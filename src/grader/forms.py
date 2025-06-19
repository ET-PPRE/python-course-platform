from django import forms

from .models import Submission


class SubmissionForm(forms.ModelForm):
    answer_script = forms.CharField(
        widget=forms.Textarea(
            attrs={
                "id": "id_answer_script",
                "rows": 15,
                "style": "width:100%; font-family:monospace;",
                "placeholder": "Write your code here…",
            }
        ),
        label="Your Solution"  # ✅ Correct place for the label
    )

    class Meta:
        model = Submission
        fields = ["answer_script"]
