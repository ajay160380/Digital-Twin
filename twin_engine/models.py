from django.db import models
from django.contrib.auth.models import User

class UserPreference(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    personality_traits = models.TextField(help_text="e.g., Early bird, Tech enthusiast, Cricket lover")
    favorite_genres = models.JSONField(default=list) 
    # Naye fields jo hum add kar rahe hain:
    diet_preference = models.CharField(max_length=50, choices=[('Veg', 'Veg'), ('Non-Veg', 'Non-Veg')], default='Veg')
    sleep_cycle = models.CharField(max_length=50, choices=[('Early Bird', 'Early Bird'), ('Night Owl', 'Night Owl')], default='Night Owl')
    favorite_color = models.CharField(max_length=50, default='Blue', help_text="Your favorite color for UI themes")

    def __str__(self):
        return f"Preferences of {self.user.username}"

class PastChoice(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    scenario = models.CharField(max_length=255) 
    choice_made = models.CharField(max_length=255) 
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} chose {self.choice_made}"
    
class TwinSettings(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    bot_nickname = models.CharField(max_length=50, default="My Twin", help_text="Nickname for your digital twin in conversations")
    
    tone_level = models.IntegerField(default=2) 
    
    preferred_language = models.CharField(max_length=20, default="Hinglish")
    
    custom_instructions = models.TextField(blank=True, null=True)
    last_mood = models.CharField(max_length=50, default="Happy", help_text="Current emotional state for mood-aware responses")

    def __str__(self):
        return f"{self.user.username}'s Twin Settings"