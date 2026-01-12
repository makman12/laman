from django import forms
from django.contrib.auth.forms import AuthenticationForm
from .models import Name, Instance, Fragment, NameType, WritingType, CompletenessType, Milieu, Series, PublicationType, Determinative


class LoginForm(AuthenticationForm):
    """Custom login form with styled widgets"""
    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'Username',
            'autofocus': True,
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': 'Password',
        })
    )


class NameForm(forms.ModelForm):
    """Form for creating/editing names"""
    class Meta:
        model = Name
        fields = [
            'name', 'name_type', 'writing_type', 'completeness', 
            'milieu', 'variant_forms', 'correspondence', 'literature', 'uncertain'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-input'}),
            'name_type': forms.Select(attrs={'class': 'form-select'}),
            'writing_type': forms.Select(attrs={'class': 'form-select'}),
            'completeness': forms.Select(attrs={'class': 'form-select'}),
            'milieu': forms.Select(attrs={'class': 'form-select'}),
            'variant_forms': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 3}),
            'correspondence': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 3}),
            'literature': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 3}),
            'uncertain': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
        }
    
    determinatives = forms.ModelMultipleChoiceField(
        queryset=Determinative.objects.all(),
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-checkbox-group'}),
        required=False
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields['determinatives'].initial = self.instance.determinatives.all()
    
    def save(self, commit=True):
        instance = super().save(commit=commit)
        if commit:
            instance.determinatives.set(self.cleaned_data['determinatives'])
        return instance


class FragmentForm(forms.ModelForm):
    """Form for creating/editing fragments"""
    class Meta:
        model = Fragment
        fields = ['series', 'fragment_number', 'publication_type']
        widgets = {
            'series': forms.Select(attrs={'class': 'form-select'}),
            'fragment_number': forms.TextInput(attrs={'class': 'form-input'}),
            'publication_type': forms.Select(attrs={'class': 'form-select'}),
        }


class InstanceForm(forms.ModelForm):
    """Form for creating/editing instances (attestations)"""
    class Meta:
        model = Instance
        fields = [
            'name', 'fragment', 'line', 'spelling', 'instance_type',
            'writing_type', 'determinative', 'completeness', 'title_epithet'
        ]
        widgets = {
            'name': forms.Select(attrs={'class': 'form-select'}),
            'fragment': forms.Select(attrs={'class': 'form-select'}),
            'line': forms.TextInput(attrs={'class': 'form-input'}),
            'spelling': forms.TextInput(attrs={'class': 'form-input'}),
            'instance_type': forms.Select(attrs={'class': 'form-select'}),
            'writing_type': forms.Select(attrs={'class': 'form-select'}),
            'determinative': forms.Select(attrs={'class': 'form-select'}),
            'completeness': forms.Select(attrs={'class': 'form-select'}),
            'title_epithet': forms.TextInput(attrs={'class': 'form-input'}),
        }


class InstanceInlineForm(forms.ModelForm):
    """Simplified form for adding instances from name detail page"""
    class Meta:
        model = Instance
        fields = [
            'fragment', 'line', 'spelling', 'instance_type',
            'writing_type', 'determinative', 'completeness', 'title_epithet'
        ]
        widgets = {
            'fragment': forms.Select(attrs={'class': 'form-select'}),
            'line': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g., obv. 5'}),
            'spelling': forms.TextInput(attrs={'class': 'form-input'}),
            'instance_type': forms.Select(attrs={'class': 'form-select'}),
            'writing_type': forms.Select(attrs={'class': 'form-select'}),
            'determinative': forms.Select(attrs={'class': 'form-select'}),
            'completeness': forms.Select(attrs={'class': 'form-select'}),
            'title_epithet': forms.TextInput(attrs={'class': 'form-input'}),
        }


# Forms for lookup tables
class NameTypeForm(forms.ModelForm):
    class Meta:
        model = NameType
        fields = ['name']
        widgets = {'name': forms.TextInput(attrs={'class': 'form-input'})}


class WritingTypeForm(forms.ModelForm):
    class Meta:
        model = WritingType
        fields = ['name']
        widgets = {'name': forms.TextInput(attrs={'class': 'form-input'})}


class CompletenessTypeForm(forms.ModelForm):
    class Meta:
        model = CompletenessType
        fields = ['name']
        widgets = {'name': forms.TextInput(attrs={'class': 'form-input'})}


class MilieuForm(forms.ModelForm):
    class Meta:
        model = Milieu
        fields = ['name']
        widgets = {'name': forms.TextInput(attrs={'class': 'form-input'})}


class SeriesForm(forms.ModelForm):
    class Meta:
        model = Series
        fields = ['name']
        widgets = {'name': forms.TextInput(attrs={'class': 'form-input'})}


class DeterminativeForm(forms.ModelForm):
    class Meta:
        model = Determinative
        fields = ['name']
        widgets = {'name': forms.TextInput(attrs={'class': 'form-input'})}
