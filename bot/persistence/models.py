"""
SQLAlchemy ORM models for GOF2BountyBot.
Provides database representations with JSON compatibility.
"""
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, Float, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.types import TypeDecorator, TEXT
from datetime import datetime
from typing import Dict, Any, Optional
import json

Base = declarative_base()

class JSONType(TypeDecorator):
    """Custom JSON type that works across different databases."""
    impl = TEXT
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is not None:
            value = json.dumps(value)
        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            value = json.loads(value)
        return value

class User(Base):
    """User entity with credits, reputation, and inventory."""
    __tablename__ = 'users'
    
    id = Column(String(50), primary_key=True)  # Discord user ID
    username = Column(String(100))
    credits = Column(Integer, default=0)
    reputation = Column(Integer, default=0)
    inventory = Column(JSONType, default=dict)
    settings = Column(JSONType, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    bounties_created = relationship("Bounty", foreign_keys="Bounty.creator_id", back_populates="creator")
    bounties_claimed = relationship("Bounty", foreign_keys="Bounty.claimed_by_id", back_populates="claimed_by")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary compatible with JSON storage."""
        return {
            "id": self.id,
            "username": self.username,
            "credits": self.credits,
            "reputation": self.reputation,
            "inventory": self.inventory or {},
            "settings": self.settings or {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'User':
        """Create User instance from dictionary."""
        user = cls()
        user.id = data.get("id")
        user.username = data.get("username")
        user.credits = data.get("credits", 0)
        user.reputation = data.get("reputation", 0)
        user.inventory = data.get("inventory", {})
        user.settings = data.get("settings", {})
        
        # Handle datetime fields
        created_str = data.get("created_at")
        if created_str:
            user.created_at = datetime.fromisoformat(created_str.replace('Z', '+00:00'))
        
        updated_str = data.get("updated_at") 
        if updated_str:
            user.updated_at = datetime.fromisoformat(updated_str.replace('Z', '+00:00'))
            
        return user

class Guild(Base):
    """Guild/Server entity with settings and configuration."""
    __tablename__ = 'guilds'
    
    id = Column(String(50), primary_key=True)  # Discord guild ID
    name = Column(String(200))
    settings = Column(JSONType, default=dict)
    prefix = Column(String(10), default="!")
    enabled_modules = Column(JSONType, default=list)
    admin_roles = Column(JSONType, default=list)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    bounties = relationship("Bounty", back_populates="guild")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary compatible with JSON storage."""
        return {
            "id": self.id,
            "name": self.name,
            "settings": self.settings or {},
            "prefix": self.prefix,
            "enabled_modules": self.enabled_modules or [],
            "admin_roles": self.admin_roles or [],
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Guild':
        """Create Guild instance from dictionary."""
        guild = cls()
        guild.id = data.get("id")
        guild.name = data.get("name")
        guild.settings = data.get("settings", {})
        guild.prefix = data.get("prefix", "!")
        guild.enabled_modules = data.get("enabled_modules", [])
        guild.admin_roles = data.get("admin_roles", [])
        
        # Handle datetime fields
        created_str = data.get("created_at")
        if created_str:
            guild.created_at = datetime.fromisoformat(created_str.replace('Z', '+00:00'))
        
        updated_str = data.get("updated_at")
        if updated_str:
            guild.updated_at = datetime.fromisoformat(updated_str.replace('Z', '+00:00'))
            
        return guild

class Bounty(Base):
    """Bounty entity for tracking bounty postings."""
    __tablename__ = 'bounties'
    
    id = Column(String(50), primary_key=True)
    guild_id = Column(String(50), ForeignKey('guilds.id'))
    creator_id = Column(String(50), ForeignKey('users.id'))
    claimed_by_id = Column(String(50), ForeignKey('users.id'), nullable=True)
    
    title = Column(String(200))
    description = Column(Text)
    reward = Column(Integer)
    criminal_name = Column(String(100))
    system_name = Column(String(100))
    status = Column(String(20), default="open")  # open, claimed, completed, cancelled
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    claimed_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    # Relationships
    guild = relationship("Guild", back_populates="bounties")
    creator = relationship("User", foreign_keys=[creator_id], back_populates="bounties_created")
    claimed_by = relationship("User", foreign_keys=[claimed_by_id], back_populates="bounties_claimed")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary compatible with JSON storage."""
        return {
            "id": self.id,
            "guild_id": self.guild_id,
            "creator_id": self.creator_id,
            "claimed_by_id": self.claimed_by_id,
            "title": self.title,
            "description": self.description,
            "reward": self.reward,
            "criminal_name": self.criminal_name,
            "system_name": self.system_name,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "claimed_at": self.claimed_at.isoformat() if self.claimed_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Bounty':
        """Create Bounty instance from dictionary."""
        bounty = cls()
        bounty.id = data.get("id")
        bounty.guild_id = data.get("guild_id")
        bounty.creator_id = data.get("creator_id")
        bounty.claimed_by_id = data.get("claimed_by_id")
        bounty.title = data.get("title")
        bounty.description = data.get("description")
        bounty.reward = data.get("reward")
        bounty.criminal_name = data.get("criminal_name")
        bounty.system_name = data.get("system_name")
        bounty.status = data.get("status", "open")
        
        # Handle datetime fields
        for field in ["created_at", "updated_at", "claimed_at", "completed_at"]:
            date_str = data.get(field)
            if date_str:
                setattr(bounty, field, datetime.fromisoformat(date_str.replace('Z', '+00:00')))
                
        return bounty

class GameData(Base):
    """Game data entity for ships, weapons, criminals, etc."""
    __tablename__ = 'game_data'
    
    id = Column(String(50), primary_key=True)
    category = Column(String(50))  # ships, weapons, criminals, systems
    name = Column(String(200))
    data = Column(JSONType)  # All game-specific data
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary compatible with JSON storage."""
        return {
            "id": self.id,
            "category": self.category,
            "name": self.name,
            "data": self.data or {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'GameData':
        """Create GameData instance from dictionary."""
        game_data = cls()
        game_data.id = data.get("id")
        game_data.category = data.get("category")
        game_data.name = data.get("name")
        game_data.data = data.get("data", {})
        
        # Handle datetime fields
        created_str = data.get("created_at")
        if created_str:
            game_data.created_at = datetime.fromisoformat(created_str.replace('Z', '+00:00'))
        
        updated_str = data.get("updated_at")
        if updated_str:
            game_data.updated_at = datetime.fromisoformat(updated_str.replace('Z', '+00:00'))
            
        return game_data
