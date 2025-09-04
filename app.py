# app.py - Main Flask Application for Intelligent Excuse Generator
import os
import json
import random
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, render_template, session, send_file
from flask_sqlalchemy import SQLAlchemy
import openai
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from PIL import Image, ImageDraw, ImageFont
import requests
from apscheduler.schedulers.background import BackgroundScheduler
from decouple import config

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = config('SECRET_KEY', default='dev-secret-key-change-in-production')
app.config['SQLALCHEMY_DATABASE_URI'] = config('DATABASE_URL', default='sqlite:///excuse_generator.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize extensions
db = SQLAlchemy(app)

# Configure APIs
openai.api_key = config('OPENAI_API_KEY', default='')

# Initialize text-to-speech (Google TTS - no PyAudio needed!)
try:
    from gtts import gTTS
    import pygame
    pygame.mixer.init()
    print("✅ Google Text-to-Speech initialized successfully!")
    tts_available = True
except ImportError:
    print("⚠️ gTTS not installed. Voice features will be disabled.")
    print("💡 To enable voice: pip install gTTS pygame")
    tts_available = False
except Exception as e:
    print(f"⚠️ TTS initialization error: {e}")
    tts_available = False

# Database Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(15))
    preferences = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    excuses = db.relationship('Excuse', backref='user', lazy=True)

class Excuse(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    scenario = db.Column(db.String(200), nullable=False)
    excuse_text = db.Column(db.Text, nullable=False)
    believability_score = db.Column(db.Float, default=0.0)
    urgency_level = db.Column(db.String(20), default='medium')
    language = db.Column(db.String(10), default='en')
    proof_generated = db.Column(db.Boolean, default=False)
    times_used = db.Column(db.Integer, default=0)
    effectiveness_rating = db.Column(db.Float, default=0.0)
    is_favorite = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_used = db.Column(db.DateTime)

class ProofDocument(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    excuse_id = db.Column(db.Integer, db.ForeignKey('excuse.id'), nullable=False)
    document_type = db.Column(db.String(50), nullable=False)
    file_path = db.Column(db.String(200), nullable=False)
    generated_at = db.Column(db.DateTime, default=datetime.utcnow)

# Excuse Generation Service
class ExcuseGenerator:
    def __init__(self):
        self.language_prompts = {
            'en': "Generate a believable excuse in English",
            'hi': "हिंदी में एक विश्वसनीय बहाना बनाएं",
            'es': "Genera una excusa creíble en español",
            'fr': "Générez une excuse crédible en français",
            'de': "Generieren Sie eine glaubwürdige Entschuldigung auf Deutsch"
        }
        
        # Load excuses from JSON file
        try:
            with open('excuses.json', 'r', encoding='utf-8') as f:
                self.excuses_db = json.load(f)
            print("✅ Loaded excuses database from excuses.json")
        except FileNotFoundError:
            print("⚠️ excuses.json not found, using minimal fallbacks")
            self.excuses_db = {
                'en': {
                    'work': {
                        'medium': ["I'm not feeling well and need to rest today."],
                        'high': ["I have an emergency that requires immediate attention."],
                        'low': ["I have some personal matters to attend to."]
                    }
                }
            }
        except Exception as e:
            print(f"❌ Error loading excuses: {e}")
            self.excuses_db = {}
    
    def generate_excuse(self, category, scenario, urgency='medium', language='en'):
        if not openai.api_key:
            print("⚠️ No OpenAI API key found. Using fallback excuses.")
            return self.get_fallback_excuse(category, scenario, urgency, language)
            
        prompt = f"""
        {self.language_prompts.get(language, self.language_prompts['en'])} for:
        
        Category: {category}
        Situation: {scenario}  
        Urgency: {urgency}
        
        Requirements:
        - Sound natural and believable
        - Appropriate for {urgency} urgency
        - 2-3 sentences maximum
        - Include specific but reasonable details
        - Professional and harmless tone
        
        Generate only the excuse text:
        """
        
        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that generates believable, professional excuses."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=150,
                temperature=0.8
            )
            
            excuse_text = response.choices[0].message['content'].strip()
            believability_score = self.calculate_believability(excuse_text, category, urgency)
            
            print(f"✅ Generated AI excuse: {excuse_text[:50]}...")
            
            return {
                'excuse': excuse_text,
                'believability_score': believability_score,
                'category': category,
                'scenario': scenario,
                'urgency': urgency
            }
            
        except Exception as e:
            print(f"❌ OpenAI API Error: {e}")
            print("🔄 Falling back to predefined excuses...")
            return self.get_fallback_excuse(category, scenario, urgency, language)
    
    def calculate_believability(self, excuse_text, category, urgency):
        score = 5.0
        length = len(excuse_text.split())
        
        if 10 <= length <= 40:
            score += 1.5
        elif length < 5 or length > 60:
            score -= 1.0
        
        specific_words = ['doctor', 'meeting', 'emergency', 'appointment', 'family', 'car', 'sick', 'traffic', 'urgent', 'hospital']
        specificity = sum(1 for word in specific_words if word in excuse_text.lower())
        score += min(specificity * 0.5, 2.0)
        
        urgency_words = {
            'high': ['emergency', 'urgent', 'immediately', 'crisis', 'hospital', 'serious'],
            'medium': ['appointment', 'meeting', 'issue', 'problem', 'doctor', 'important'],
            'low': ['feeling', 'might', 'possibly', 'may', 'think', 'probably']
        }
        
        if any(word in excuse_text.lower() for word in urgency_words.get(urgency, [])):
            score += 1.5
        
        return min(score, 10.0)
    
    def get_fallback_excuse(self, category, scenario, urgency, language='en'):
        # Get excuses from loaded database
        try:
            language_excuses = self.excuses_db.get(language, self.excuses_db.get('en', {}))
            category_excuses = language_excuses.get(category, language_excuses.get('work', {}))
            excuse_options = category_excuses.get(urgency, category_excuses.get('medium', ['I need to handle something important today.']))
            
            # Randomly select an excuse
            excuse_text = random.choice(excuse_options)
            
            # Calculate believability score
            base_score = {'low': 6.5, 'medium': 7.5, 'high': 8.5}
            score = base_score.get(urgency, 7.5) + random.uniform(-0.8, 1.2)
            
            print(f"📝 Selected excuse from database: {excuse_text[:50]}...")
            
            return {
                'excuse': excuse_text,
                'believability_score': min(max(score, 5.0), 10.0),
                'category': category,
                'scenario': scenario,
                'urgency': urgency
            }
            
        except Exception as e:
            print(f"❌ Error selecting excuse: {e}")
            return {
                'excuse': "I have an unexpected situation that requires my attention.",
                'believability_score': 7.0,
                'category': category,
                'scenario': scenario,
                'urgency': urgency
            }

excuse_generator = ExcuseGenerator()

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/generate-excuse', methods=['POST'])
def generate_excuse():
    data = request.get_json()
    
    category = data.get('category', 'work')
    scenario = data.get('scenario', 'general')
    urgency = data.get('urgency', 'medium')
    language = data.get('language', 'en')
    user_id = data.get('user_id', 1)
    
    print(f"🎯 Generating excuse: {category}/{urgency} - {scenario} ({language})")
    
    excuse_data = excuse_generator.generate_excuse(category, scenario, urgency, language)
    
    # Create default user if doesn't exist
    user = User.query.get(user_id)
    if not user:
        user = User(id=1, username='demo_user', email='demo@example.com')
        db.session.add(user)
        db.session.commit()
        print("👤 Created demo user")
    
    # Save excuse
    excuse = Excuse(
        user_id=user_id,
        category=category,
        scenario=scenario,
        excuse_text=excuse_data['excuse'],
        believability_score=excuse_data['believability_score'],
        urgency_level=urgency,
        language=language
    )
    
    db.session.add(excuse)
    db.session.commit()
    
    print(f"💾 Saved excuse #{excuse.id} with score {excuse_data['believability_score']:.1f}")
    
    return jsonify({
        'success': True,
        'excuse_id': excuse.id,
        'excuse': excuse_data['excuse'],
        'believability_score': excuse_data['believability_score'],
        'category': category,
        'urgency': urgency
    })

@app.route('/api/generate-proof', methods=['POST'])
def generate_proof():
    data = request.get_json()
    excuse_id = data.get('excuse_id')
    proof_type = data.get('proof_type', 'email')
    
    excuse = Excuse.query.get(excuse_id)
    if not excuse:
        return jsonify({'success': False, 'error': 'Excuse not found'})
    
    print(f"📄 Generating {proof_type} proof for excuse #{excuse_id}")
    
    proof_path = generate_proof_document(excuse, proof_type)
    
    if proof_path:
        proof_doc = ProofDocument(
            excuse_id=excuse_id,
            document_type=proof_type,
            file_path=proof_path
        )
        db.session.add(proof_doc)
        
        excuse.proof_generated = True
        db.session.commit()
        
        print(f"✅ Proof document created: {proof_path}")
        
        return jsonify({
            'success': True,
            'proof_path': proof_path,
            'download_url': f'/static/proofs/{os.path.basename(proof_path)}'
        })
    
    return jsonify({'success': False, 'error': 'Failed to generate proof'})

@app.route('/api/voice-excuse', methods=['POST'])
def voice_excuse():
    data = request.get_json()
    excuse_id = data.get('excuse_id')
    
    excuse = Excuse.query.get(excuse_id)
    if not excuse:
        return jsonify({'success': False, 'error': 'Excuse not found'})
    
    if not tts_available:
        return jsonify({
            'success': False, 
            'error': 'Voice features not available. Install with: pip install gTTS pygame'
        })
    
    try:
        print(f"🎤 Converting excuse #{excuse_id} to speech...")
        
        # Create audio filename
        audio_filename = f"excuse_{excuse_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp3"
        audio_path = f"static/audio/{audio_filename}"
        
        # Create directory if it doesn't exist
        os.makedirs("static/audio", exist_ok=True)
        
        # Select language for TTS
        tts_language = excuse.language if excuse.language in ['en', 'hi', 'es', 'fr', 'de'] else 'en'
        
        # Generate speech using Google TTS
        tts = gTTS(text=excuse.excuse_text, lang=tts_language, slow=False)
        tts.save(audio_path)
        
        print(f"✅ Voice file generated: {audio_path} (Language: {tts_language})")
        
        return jsonify({
            'success': True,
            'audio_url': f'/{audio_path}',
            'message': f'Voice file generated successfully in {tts_language}!'
        })
    
    except Exception as e:
        print(f"❌ TTS Error: {str(e)}")
        return jsonify({'success': False, 'error': f'Voice generation failed: {str(e)}'})

@app.route('/api/excuse-history')
def excuse_history():
    user_id = request.args.get('user_id', 1)
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    
    excuses = Excuse.query.filter_by(user_id=user_id).order_by(Excuse.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    excuse_list = []
    for excuse in excuses.items:
        excuse_list.append({
            'id': excuse.id,
            'category': excuse.category,
            'scenario': excuse.scenario,
            'excuse_text': excuse.excuse_text,
            'believability_score': excuse.believability_score,
            'times_used': excuse.times_used,
            'is_favorite': excuse.is_favorite,
            'created_at': excuse.created_at.isoformat()
        })
    
    return jsonify({
        'success': True,
        'excuses': excuse_list,
        'total': excuses.total,
        'pages': excuses.pages,
        'current_page': page
    })

def generate_proof_document(excuse, proof_type):
    """Generate proof documents"""
    try:
        if proof_type == 'email':
            return generate_fake_email(excuse)
        elif proof_type == 'receipt':
            return generate_fake_receipt(excuse)
        elif proof_type == 'medical_note':
            return generate_medical_note(excuse)
    except Exception as e:
        print(f"❌ Error generating proof: {e}")
        return None

def generate_fake_email(excuse):
    """Generate fake email screenshot"""
    try:
        img = Image.new('RGB', (800, 600), color='white')
        draw = ImageDraw.Draw(img)
        
        try:
            font = ImageFont.load_default()
            title_font = ImageFont.load_default()
        except:
            font = None
            title_font = None
        
        # Email header background
        draw.rectangle([0, 0, 800, 120], fill='#f8f9fa', outline='#dee2e6')
        
        # Email header details
        draw.text((20, 20), "From: emergency@company.com", fill='#333333', font=title_font)
        draw.text((20, 45), "To: manager@workplace.com", fill='#333333', font=font)
        draw.text((20, 70), f"Subject: {excuse.category.title()} - Unable to attend", fill='#333333', font=title_font)
        draw.text((20, 95), f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}", fill='#666666', font=font)
        
        # Email body
        y_pos = 150
        words = excuse.excuse_text.split()
        line = ""
        
        for word in words:
            if len(line + word) < 70:
                line += word + " "
            else:
                draw.text((30, y_pos), line, fill='#333333', font=font)
                y_pos += 30
                line = word + " "
        
        if line:
            draw.text((30, y_pos), line, fill='#333333', font=font)
        
        # Footer
        draw.text((30, y_pos + 50), "Best regards,", fill='#333333', font=font)
        draw.text((30, y_pos + 80), "Emergency Contact", fill='#333333', font=font)
        
        # Save image
        filename = f"email_{excuse.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        filepath = f"static/proofs/{filename}"
        os.makedirs("static/proofs", exist_ok=True)
        img.save(filepath)
        
        return filepath
    except Exception as e:
        print(f"Error creating email: {e}")
        return None

def generate_fake_receipt(excuse):
    """Generate fake service receipt"""
    try:
        filename = f"receipt_{excuse.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        filepath = f"static/proofs/{filename}"
        os.makedirs("static/proofs", exist_ok=True)
        
        c = canvas.Canvas(filepath, pagesize=letter)
        width, height = letter
        
        # Header
        c.setFont("Helvetica-Bold", 16)
        c.drawString(100, height - 100, "EMERGENCY SERVICE RECEIPT")
        
        c.setFont("Helvetica", 12)
        c.drawString(100, height - 130, f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        c.drawString(100, height - 150, f"Receipt #: ESR-{random.randint(100000, 999999)}")
        c.drawString(100, height - 170, f"Service ID: SVC-{random.randint(1000, 9999)}")
        
        # Service details
        c.setFont("Helvetica-Bold", 12)
        c.drawString(100, height - 210, "Service Details:")
        
        c.setFont("Helvetica", 11)
        c.drawString(100, height - 235, f"Category: {excuse.category.title()} Emergency Response")
        c.drawString(100, height - 255, f"Description: {excuse.excuse_text[:60]}...")
        c.drawString(100, height - 275, "Status: Service Completed")
        c.drawString(100, height - 295, "Priority: Urgent")
        c.drawString(100, height - 315, "Amount: No Charge (Emergency Service)")
        
        # Footer
        c.setFont("Helvetica-Bold", 10)
        c.drawString(100, height - 360, "Emergency Services Provider")
        c.drawString(100, height - 380, "Available 24/7 for urgent situations")
        c.drawString(100, height - 400, "Thank you for using our emergency response service")
        
        c.save()
        return filepath
    except Exception as e:
        print(f"Error creating receipt: {e}")
        return None

def generate_medical_note(excuse):
    """Generate fake medical note"""
    try:
        filename = f"medical_{excuse.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        filepath = f"static/proofs/{filename}"
        os.makedirs("static/proofs", exist_ok=True)
        
        c = canvas.Canvas(filepath, pagesize=letter)
        width, height = letter
        
        # Header
        c.setFont("Helvetica-Bold", 16)
        c.drawString(100, height - 100, "MEDICAL CONSULTATION NOTE")
        
        c.setFont("Helvetica-Bold", 12)
        c.drawString(100, height - 130, "Healthcare Services Center")
        c.drawString(100, height - 150, "Professional Medical Care")
        
        c.setFont("Helvetica", 11)
        c.drawString(100, height - 180, f"Date: {datetime.now().strftime('%Y-%m-%d')}")
        c.drawString(100, height - 200, f"Time: {datetime.now().strftime('%H:%M')}")
        c.drawString(100, height - 220, f"Reference: MED-{random.randint(10000, 99999)}")
        
        # Medical details
        c.setFont("Helvetica-Bold", 12)
        c.drawString(100, height - 260, "Medical Assessment:")
        
        c.setFont("Helvetica", 11)
        c.drawString(100, height - 285, "Patient consultation has been completed.")
        c.drawString(100, height - 305, f"Condition: {excuse.excuse_text}")
        c.drawString(100, height - 325, "Medical recommendation: Rest and recovery as advised")
        c.drawString(100, height - 345, "Follow-up: As medically necessary")
        c.drawString(100, height - 365, f"Next review: {(datetime.now() + timedelta(days=3)).strftime('%Y-%m-%d')}")
        
        # Footer
        c.setFont("Helvetica", 10)
        c.drawString(100, height - 420, "Healthcare Professional")
        c.drawString(100, height - 440, "Licensed Medical Provider")
        c.drawString(100, height - 460, f"License #: MP-{random.randint(100000, 999999)}")
        
        c.save()
        return filepath
    except Exception as e:
        print(f"Error creating medical note: {e}")
        return None

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        print("📊 Database tables created successfully!")
    
    print("🎉 Intelligent Excuse Generator is starting...")
    print("📱 Access the app at: http://localhost:5000")
    
    if tts_available:
        print("🎤 Voice features enabled! (Google TTS)")
    else:
        print("🔇 Voice features disabled (install gTTS pygame to enable)")
        
    if openai.api_key:
        print("🤖 OpenAI API configured - AI features enabled!")
    else:
        print("🤖 No OpenAI API key - using fallback excuses")
        
    print("=" * 60)
    app.run(debug=True, host='0.0.0.0', port=5000)
