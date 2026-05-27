from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.db.models import Q
from .models import (
    Name, Instance, Fragment, NameType, WritingType, CompletenessType,
    Milieu, Series, PublicationType, Determinative, DeterminativeVariant
)


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
        current_ids = []
        if self.instance.pk:
            current_ids = list(self.instance.determinatives.values_list('id', flat=True))
            self.fields['determinatives'].initial = self.instance.determinatives.all()
        self.fields['determinatives'].queryset = Determinative.objects.filter(
            Q(is_active=True) | Q(pk__in=current_ids)
        ).order_by('name')
    
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


class InstanceDeterminativeMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'determinative' not in self.fields:
            self.fields['determinative'] = forms.ModelChoiceField(
                queryset=Determinative.objects.none(),
                required=False,
                widget=forms.Select(attrs={'class': 'form-select'}),
                label='Determinative',
            )
        if 'determinative_variant_value' not in self.fields:
            self.fields['determinative_variant_value'] = forms.CharField(
                required=False,
                widget=forms.TextInput(attrs={'class': 'form-input'}),
                label='Attested Form',
            )
        current_id = self.instance.determinative.id if getattr(self.instance, 'determinative', None) else None
        self.fields['determinative'].queryset = Determinative.objects.filter(
            Q(is_active=True) | Q(pk=current_id)
        ).order_by('name')
        if getattr(self.instance, 'pk', None) and self.instance.determinative_variant_id:
            self.fields['determinative'].initial = self.instance.determinative
            self.fields['determinative_variant_value'].initial = self.instance.determinative_variant.value

    def clean(self):
        cleaned_data = super().clean()
        determinative = cleaned_data.get('determinative')
        variant_value = Determinative.clean_variant_value(
            cleaned_data.get('determinative_variant_value', '')
        )

        if variant_value and not determinative:
            raise forms.ValidationError('Select a determinative when entering an attested form.')

        resolved_variant = None
        if determinative:
            if variant_value:
                resolved_variant = DeterminativeVariant.get_or_create_for_value(
                    variant_value,
                    determinative=determinative,
                )
            else:
                resolved_variant = determinative.preferred_variant or DeterminativeVariant.get_or_create_for_value(
                    determinative.name,
                    determinative=determinative,
                    is_preferred=True,
                )
        cleaned_data['determinative_variant_value'] = variant_value
        cleaned_data['resolved_determinative_variant'] = resolved_variant
        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.determinative_variant = self.cleaned_data.get('resolved_determinative_variant')
        if commit:
            instance.save()
            if hasattr(self, 'save_m2m'):
                self.save_m2m()
        return instance


class InstanceForm(InstanceDeterminativeMixin, forms.ModelForm):
    """Form for creating/editing instances (attestations)"""
    class Meta:
        model = Instance
        fields = [
            'name', 'fragment', 'line', 'spelling', 'instance_type',
            'writing_type', 'completeness', 'title_epithet'
        ]
        widgets = {
            'name': forms.Select(attrs={'class': 'form-select'}),
            'fragment': forms.Select(attrs={'class': 'form-select'}),
            'line': forms.TextInput(attrs={'class': 'form-input'}),
            'spelling': forms.TextInput(attrs={'class': 'form-input'}),
            'instance_type': forms.Select(attrs={'class': 'form-select'}),
            'writing_type': forms.Select(attrs={'class': 'form-select'}),
            'completeness': forms.Select(attrs={'class': 'form-select'}),
            'title_epithet': forms.TextInput(attrs={'class': 'form-input'}),
        }


class InstanceInlineForm(InstanceDeterminativeMixin, forms.ModelForm):
    """Simplified form for adding instances from name detail page"""
    class Meta:
        model = Instance
        fields = [
            'fragment', 'line', 'spelling', 'instance_type',
            'writing_type', 'completeness', 'title_epithet'
        ]
        widgets = {
            'fragment': forms.Select(attrs={'class': 'form-select'}),
            'line': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g., obv. 5'}),
            'spelling': forms.TextInput(attrs={'class': 'form-input'}),
            'instance_type': forms.Select(attrs={'class': 'form-select'}),
            'writing_type': forms.Select(attrs={'class': 'form-select'}),
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
        fields = ['name', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-input'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
        }

    def clean_name(self):
        name = Determinative.normalize_name(self.cleaned_data['name'])
        if not Determinative.is_valid_parent_name(name):
            raise forms.ValidationError('Enter a non-empty determinative name.')
        return name


class DeterminativeVariantForm(forms.ModelForm):
    class Meta:
        model = DeterminativeVariant
        fields = ['value', 'variant_kind', 'is_preferred']
        widgets = {
            'value': forms.TextInput(attrs={'class': 'form-input'}),
            'variant_kind': forms.Select(attrs={'class': 'form-select'}),
            'is_preferred': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
        }

    def clean_value(self):
        value = Determinative.clean_variant_value(self.cleaned_data['value'])
        if not value:
            raise forms.ValidationError('Variant value cannot be empty.')
        return value


class DeterminativeMergeForm(forms.Form):
    source = forms.ModelChoiceField(
        queryset=Determinative.objects.none(),
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Merge from',
    )
    target = forms.ModelChoiceField(
        queryset=Determinative.objects.none(),
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Merge into',
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        qs = Determinative.objects.order_by('name')
        self.fields['source'].queryset = qs
        self.fields['target'].queryset = qs

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get('source') == cleaned_data.get('target'):
            raise forms.ValidationError('Choose two different determinatives.')
        return cleaned_data
