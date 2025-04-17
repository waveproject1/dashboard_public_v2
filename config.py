import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'bardzo-tajny-klucz'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///orders.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Konfiguracja Discord bota
    DISCORD_TOKEN = 'NzgzMDEyMjQ4MTI1MTc3ODc2.G1LZwM.t3nr49o4qwds68IXAMtZLrVcrwe7Mhj2ZkJ4aY'
    DISCORD_CHANNEL_ID = 1234567890  # ID kanału do powiadomień