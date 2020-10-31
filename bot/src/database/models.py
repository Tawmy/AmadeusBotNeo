import enum

from sqlalchemy import Column, ForeignKey, Integer, BigInteger, SmallInteger, String, DateTime, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship


class MessageEventType(enum.Enum):
    DELETE = 0
    EDIT = 1


class NameType(enum.Enum):
    USERNAME = 0
    NICKNAME = 1


Base = declarative_base()


class User(Base):
    __tablename__ = "user"
    id = Column(BigInteger, primary_key=True, autoincrement=False)
    messages = relationship("Message", cascade="all, delete")
    names = relationship("Name", cascade="all, delete")
    avatars = relationship("Avatar", cascade="all, delete")


class Message(Base):
    __tablename__ = "message"
    id = Column(BigInteger, primary_key=True, autoincrement=False)
    guild_id = Column(BigInteger, nullable=False)
    channel_id = Column(BigInteger, nullable=False)
    user_id = Column(BigInteger, ForeignKey('user.id'), nullable=False)
    created_at = Column(DateTime, nullable=False)
    content = Column(String, nullable=False)
    count_mentions = Column(SmallInteger, nullable=False)
    count_attachments = Column(SmallInteger, nullable=False)
    count_embeds = Column(SmallInteger, nullable=False)
    event_type = Column(Enum(MessageEventType), nullable=False)
    event_at = Column(DateTime, nullable=False)
    before = Column(String)
    attachment = relationship("Attachment", cascade="all, delete")


class Attachment(Base):
    __tablename__ = "attachment"
    id = Column(Integer, primary_key=True)
    message_id = Column(BigInteger, ForeignKey('message.id'), nullable=False)
    filename = Column(String, nullable=False)


class Avatar(Base):
    __tablename__ = "avatar"
    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, ForeignKey('user.id'), nullable=False)
    set_at = Column(DateTime, nullable=False)


class Name(Base):
    __tablename__ = "name"
    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, ForeignKey('user.id'), nullable=False)
    set_at = Column(DateTime, nullable=False)
    name_type = Column(Enum(NameType), nullable=False)
    name_before = Column(String, nullable=False)
    name_after = Column(String, nullable=False)
