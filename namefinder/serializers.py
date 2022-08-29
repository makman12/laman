from rest_framework import serializers 

from .models import Name,Instance

class NameSerializer(serializers.ModelSerializer):
 
    class Meta:
        model = Name
        # add all columns from the model
        fields = '__all__'
    
    class Tag(serializers.ModelSerializer):
        class Meta:
            model = Name
            fields = ('name_id',"name_clean","type","completeness","writing_clean")
            # order according to the name_clean field
            


class InstanceSerializer(serializers.ModelSerializer):
 
    class Meta:
        model = Instance
        # add all columns from the model
        fields = '__all__'
        