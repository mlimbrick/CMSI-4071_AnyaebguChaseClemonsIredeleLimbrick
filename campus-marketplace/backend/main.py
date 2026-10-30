from datetime import datetime, timedelta, timezone
from pathlib import Path
import os
from typing import Optional
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import create_engine, String, Integer, ForeignKey, select, or_, inspect, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, Session, sessionmaker

DATABASE_URL = os.getenv('DATABASE_URL', f"sqlite:///{Path(__file__).parent / 'marketplace.db'}")
SECRET_KEY = os.getenv('SECRET_KEY', 'dev-only-change-this-secret-before-deploying')
engine = create_engine(DATABASE_URL, connect_args={'check_same_thread': False} if DATABASE_URL.startswith('sqlite') else {})
SessionLocal = sessionmaker(bind=engine)
class Base(DeclarativeBase): pass
class User(Base):
    __tablename__ = 'users'
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20), default='customer')
    campus: Mapped[str] = mapped_column(String(100), default='LMU')
    graduation_year: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    business_name: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    bio: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    listings: Mapped[list['Listing']] = relationship(back_populates='vendor', cascade='all, delete-orphan')
class Listing(Base):
    __tablename__ = 'listings'
    id: Mapped[int] = mapped_column(primary_key=True)
    vendor_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    title: Mapped[str] = mapped_column(String(120))
    description: Mapped[str] = mapped_column(String(1000))
    category: Mapped[str] = mapped_column(String(60))
    price: Mapped[int] = mapped_column(Integer)
    location: Mapped[str] = mapped_column(String(120))
    image: Mapped[str] = mapped_column(String(500), default='')
    active: Mapped[bool] = mapped_column(default=True)
    vendor: Mapped[User] = relationship(back_populates='listings')
# Preserve existing prototype databases when adding the optional profile field.
if inspect(engine).has_table('users'):
    columns = {column['name'] for column in inspect(engine).get_columns('users')}
    if 'graduation_year' not in columns:
        with engine.begin() as connection:
            connection.execute(text('ALTER TABLE users ADD COLUMN graduation_year INTEGER'))
Base.metadata.create_all(engine)
app = FastAPI(title='Campus Marketplace API', version='0.9.0')
app.add_middleware(CORSMiddleware, allow_origins=os.getenv('FRONTEND_ORIGINS','http://localhost:5173,http://127.0.0.1:5173').split(','), allow_credentials=True, allow_methods=['*'], allow_headers=['*'])
security = HTTPBearer(auto_error=False)
pwd = CryptContext(schemes=['bcrypt'], deprecated='auto')
def db_session():
    with SessionLocal() as db: yield db
def current_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security), db: Session = Depends(db_session)):
    if not credentials: raise HTTPException(401, 'Please log in')
    try:
        data = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=['HS256'])
        user = db.get(User, int(data['sub']))
    except (JWTError, ValueError, KeyError): raise HTTPException(401, 'Invalid session')
    if not user: raise HTTPException(401, 'Account not found')
    return user
class Register(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)
    role: str = 'customer'
    campus: str = 'LMU'
    graduation_year: Optional[int] = Field(default=None, ge=1900, le=2200)
    business_name: Optional[str] = None
class Login(BaseModel):
    email: EmailStr
    password: str
class ListingIn(BaseModel):
    title: str = Field(min_length=3, max_length=120)
    description: str = Field(min_length=5, max_length=1000)
    category: str
    price: int = Field(ge=0, le=1000000)
    location: str = Field(min_length=2, max_length=120)
    image: str = ''
    active: bool = True
class ProfileIn(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    business_name: str = Field(default="", max_length=120)
    bio: str = Field(max_length=500)
def user_out(u):
    return {'id':u.id,'name':u.name,'email':u.email,'role':u.role,'campus':u.campus,'graduation_year':u.graduation_year,'business_name':u.business_name,'bio':u.bio}
def listing_out(l):
    return {'id':l.id,'vendor_id':l.vendor_id,'vendor_name':l.vendor.business_name or l.vendor.name,'campus':l.vendor.campus,'title':l.title,'description':l.description,'category':l.category,'price':l.price,'location':l.location,'image':l.image,'active':l.active}
def token(u):
    return jwt.encode({'sub':str(u.id),'exp':datetime.now(timezone.utc)+timedelta(days=7)},SECRET_KEY,algorithm='HS256')
@app.get('/health')
def health(): return {'status':'ok'}
@app.post('/auth/register', status_code=201)
def register(body:Register, db:Session=Depends(db_session)):
    if body.role not in ('customer','vendor'): raise HTTPException(400,'Invalid role')
    if not body.email.lower().endswith('.edu'): raise HTTPException(400,'Use a college .edu email address')
    if db.scalar(select(User).where(User.email==body.email.lower())): raise HTTPException(409,'Email already registered')
    u=User(name=body.name,email=body.email.lower(),password_hash=pwd.hash(body.password),role=body.role,campus=body.campus,graduation_year=body.graduation_year,business_name=body.business_name if body.role=='vendor' else None)
    db.add(u);db.commit();db.refresh(u)
    return {'token':token(u),'user':user_out(u)}
@app.post('/auth/login')
def login(body:Login,db:Session=Depends(db_session)):
    u=db.scalar(select(User).where(User.email==body.email.lower()))
    if not u or not pwd.verify(body.password,u.password_hash): raise HTTPException(401,'Incorrect email or password')
    return {'token':token(u),'user':user_out(u)}
@app.get('/me')
def me(u:User=Depends(current_user)): return user_out(u)
@app.patch('/me/profile')
def profile(body:ProfileIn,u:User=Depends(current_user),db:Session=Depends(db_session)):
    if u.role == 'vendor' and len(body.business_name.strip()) < 2:
        raise HTTPException(400, 'Business name must contain at least two characters')
    u.name=body.name;u.business_name=body.business_name if u.role == 'vendor' else None;u.bio=body.bio;db.commit();return user_out(u)
@app.get('/listings')
def listings(search:str='',category:str='',campus:str='',db:Session=Depends(db_session)):
    q=select(Listing).join(User).where(Listing.active==True)
    if search: q=q.where(or_(Listing.title.ilike(f'%{search}%'),Listing.description.ilike(f'%{search}%'),User.business_name.ilike(f'%{search}%')))
    if category: q=q.where(Listing.category==category)
    if campus: q=q.where(User.campus==campus)
    return [listing_out(l) for l in db.scalars(q.order_by(Listing.id.desc())).all()]
@app.get('/my/listings')
def my_listings(u:User=Depends(current_user),db:Session=Depends(db_session)):
    return [listing_out(l) for l in db.scalars(select(Listing).where(Listing.vendor_id==u.id).order_by(Listing.id.desc())).all()]
@app.post('/listings',status_code=201)
def create_listing(body:ListingIn,u:User=Depends(current_user),db:Session=Depends(db_session)):
    if u.role!='vendor':raise HTTPException(403,'Vendor account required')
    l=Listing(vendor_id=u.id,**body.model_dump());db.add(l);db.commit();db.refresh(l);return listing_out(l)
@app.put('/listings/{listing_id}')
def update_listing(listing_id:int,body:ListingIn,u:User=Depends(current_user),db:Session=Depends(db_session)):
    l=db.get(Listing,listing_id)
    if not l:raise HTTPException(404,'Listing not found')
    if l.vendor_id!=u.id:raise HTTPException(403,'Not your listing')
    for key,value in body.model_dump().items():setattr(l,key,value)
    db.commit();return listing_out(l)
@app.delete('/listings/{listing_id}',status_code=204)
def delete_listing(listing_id:int,u:User=Depends(current_user),db:Session=Depends(db_session)):
    l=db.get(Listing,listing_id)
    if not l:raise HTTPException(404,'Listing not found')
    if l.vendor_id!=u.id:raise HTTPException(403,'Not your listing')
    db.delete(l);db.commit()
@app.get('/vendors/{vendor_id}')
def vendor(vendor_id:int,db:Session=Depends(db_session)):
    u=db.get(User,vendor_id)
    if not u or u.role!='vendor':raise HTTPException(404,'Vendor not found')
    return {'vendor':user_out(u),'listings':[listing_out(l) for l in u.listings if l.active]}
