from django.contrib import admin

# Register your models here.

from .models import Name,Instance
from django.db import models
from django.forms import TextInput, Textarea


class InstanceInline(admin.TabularInline):
    model = Instance
    extra = 0
    formfield_overrides = {
        models.CharField: {'widget': TextInput(attrs={'size':'20'})},
        models.TextField: {'widget': Textarea(attrs={'rows':1, 'cols':10})},
    }

@admin.register(Name)
class NameAdmin(admin.ModelAdmin):
    list_display = ('name_id', 'name_clean', 'type')
    search_fields = ['query',"name_clean"]
    inlines = [InstanceInline]
    formfield_overrides = {
        models.CharField: {'widget': TextInput(attrs={'size':'20'})},
        models.TextField: {'widget': Textarea(attrs={'rows':1, 'cols':10})},
    }


# change title
admin.site.site_header = 'Laman Hittite Name Finder'

from django.contrib.admin.models import ADDITION, LogEntry

LogEntry.objects.filter(action_flag=ADDITION)