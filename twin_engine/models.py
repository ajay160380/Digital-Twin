from django.db import models
from django.contrib.auth.models import User

class UserPreference(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    # blank=True, null=True add kiya taaki empty form submit hone par error na aaye
    personality_traits = models.TextField(blank=True, null=True, help_text="e.g., Early bird, Tech enthusiast, Cricket lover")
    favorite_genres = models.JSONField(default=list, blank=True) 
    
    # Naye fields
    diet_preference = models.CharField(max_length=50, choices=[('Veg', 'Veg'), ('Non-Veg', 'Non-Veg')], default='Veg')
    sleep_cycle = models.CharField(max_length=50, choices=[('Early Bird', 'Early Bird'), ('Night Owl', 'Night Owl')], default='Night Owl')
    favorite_color = models.CharField(max_length=50, default='Blue', help_text="Your favorite color for UI themes")

    def __str__(self):
        return f"Preferences of {self.user.username}"

class PastChoice(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    
    # 🔥 BIG FIX: CharField(max_length=255) ko TextField me badal diya. 
    # Ab AI kitna bhi lamba response de, database crash nahi hoga!
    scenario = models.TextField(help_text="The situation given to the AI") 
    choice_made = models.TextField(help_text="The AI's prediction/response") 
    
    # ✅ YEH NAYA FIELD ADD KIYA HAI ACCURACY RATING KE LIYE
    is_accurate = models.BooleanField(null=True, blank=True, help_text="Did the user agree with this?")
    
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.timestamp.strftime('%Y-%m-%d %H:%M')}"
    
class TwinSettings(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    bot_nickname = models.CharField(max_length=50, default="My Twin", help_text="Nickname for your digital twin in conversations")
    
    tone_level = models.IntegerField(default=2) 
    
    preferred_language = models.CharField(max_length=20, default="Hinglish")
    
    custom_instructions = models.TextField(blank=True, null=True)
    last_mood = models.CharField(max_length=50, default="Happy", help_text="Current emotional state for mood-aware responses")

    def __str__(self):
        return f"{self.user.username}'s Twin Settings"