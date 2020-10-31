import enum

from sqlalchemy import Column, ForeignKey, Integer, BigInteger, SmallInteger, String, DateTime, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, backref


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


class Message(Base):
    __tablename__ = "message"
    id = Column(BigInteger, primary_key=True, autoincrement=False)
    guild_id = Column(BigInteger, nullable=False)
    channel_id = Column(BigInteger, nullable=False)
    user_id = Column(BigInteger, ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    created_at = Column(DateTime, nullable=False)
    content = Column(String, nullable=False)
    count_mentions = Column(SmallInteger, nullable=False)
    count_attachments = Column(SmallInteger, nullable=False)
    count_embeds = Column(SmallInteger, nullable=False)
    event_type = Column(Enum(MessageEventType), nullable=False)
    event_at = Column(DateTime, nullable=False)
    before = Column(String)
    parent = relationship('User', backref=backref('Messages', passive_deletes=True))


class Attachment(Base):
    __tablename__ = "attachment"
    id = Column(Integer, primary_key=True)
    message_id = Column(BigInteger, ForeignKey('message.id', ondelete='CASCADE'), nullable=False)
    filename = Column(String, nullable=False)
    parent = relationship('Message', backref=backref('Attachments', passive_deletes=True))


class Avatar(Base):
    __tablename__ = "avatar"
    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    set_at = Column(DateTime, nullable=False)
    parent = relationship('User', backref=backref('Avatars', passive_deletes=True))


class Name(Base):
    __tablename__ = "name"
    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    set_at = Column(DateTime, nullable=False)
    name_type = Column(Enum(NameType), nullable=False)
    name_before = Column(String, nullable=False)
    name_after = Column(String, nullable=False)
    parent = relationship('User', backref=backref('Names', passive_deletes=True))
