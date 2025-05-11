import yaml
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
from typing import Optional, Dict, Any

class ProfileManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        self.config_path = Path(__file__).parent / 'config.yml'
        self.profiles: Dict[str, Any] = {}
        self.active_profile: Optional[str] = None
        self.load_config()

    def load_config(self):
        """Load configuration from YAML file"""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Config file not found: {self.config_path}")

        with open(self.config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
            self.profiles = config.get('profiles', {})
            self.active_profile = config.get('in-used-profile')

            if not self.active_profile:
                raise ValueError("No active profile specified in config.yml")
            if self.active_profile not in self.profiles:
                raise ValueError(f"Active profile '{self.active_profile}' not found in profiles")

    def get_active_profile(self) -> Dict[str, Any]:
        """Get the currently active profile configuration"""
        return self.profiles[self.active_profile]

    def get_db_path(self) -> str:
        """Get database path for active profile"""
        return self.get_active_profile()['db']

    def get_engine(self):
        """Get SQLAlchemy engine for active profile"""
        db_path = self.get_db_path()
        return create_engine(f'sqlite:///{db_path}')
    
    def get_hoadondientu_credentials(self):
        """Get hoadondientu credentials from active profile"""
        profile = self.get_active_profile()
        credentials = profile.get('hoadondientu')
        if not credentials:
            raise ValueError(f"No hoadondientu credentials found in profile '{self.active_profile}'")
        return credentials.get('username'), credentials.get('password')

    @contextmanager
    def get_session(self) -> Session:
        """Get SQLAlchemy session for active profile"""
        engine = self.get_engine()
        SessionLocal = sessionmaker(bind=engine)
        session = SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

# Global instance
profile_manager = ProfileManager()