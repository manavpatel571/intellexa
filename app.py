from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
import os
import sqlite3
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
import google.generativeai as genai
from pypdf import PdfReader
import json
from dotenv import load_dotenv
import re

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Configuration
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max file size
GEMINI_API_KEY = os.getenv('GOOGLE_API_KEY')

# Configure Gemini AI
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    model_name = 'gemini-2.5-flash-lite'  # User's preferred model
    print(f"Initializing Gemini AI with model: {model_name}")
    try:
        model = genai.GenerativeModel(model_name)
        print(f"✓ Gemini AI model initialized successfully")
    except Exception as e:
        print(f"ERROR: Failed to initialize model '{model_name}': {e}")
        print(f"Available models might be: gemini-pro, gemini-1.5-pro, gemini-1.5-flash")
        model = None
else:
    print("Warning: GOOGLE_API_KEY not found in .env file")
    model = None

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Database initialization
def init_db():
    conn = sqlite3.connect('intellexa.db')
    c = conn.cursor()
    
    # Users table
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # Study materials table
    c.execute('''CREATE TABLE IF NOT EXISTS materials (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        subject TEXT,
        file_type TEXT,
        file_path TEXT,
        text_content TEXT,
        summary TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )''')
    
    # Flashcards table
    c.execute('''CREATE TABLE IF NOT EXISTS flashcards (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        material_id INTEGER NOT NULL,
        question TEXT NOT NULL,
        answer TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (material_id) REFERENCES materials(id)
    )''')
    
    # Quizzes table
    c.execute('''CREATE TABLE IF NOT EXISTS quizzes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        material_id INTEGER NOT NULL,
        question TEXT NOT NULL,
        options TEXT NOT NULL,
        correct_answer INTEGER NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (material_id) REFERENCES materials(id)
    )''')
    
    # Quiz attempts table
    c.execute('''CREATE TABLE IF NOT EXISTS quiz_attempts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        material_id INTEGER NOT NULL,
        score INTEGER NOT NULL,
        total_questions INTEGER NOT NULL,
        completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id),
        FOREIGN KEY (material_id) REFERENCES materials(id)
    )''')
    
    # User activity table
    c.execute('''CREATE TABLE IF NOT EXISTS user_activity (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        material_id INTEGER,
        activity_type TEXT NOT NULL,
        duration INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id),
        FOREIGN KEY (material_id) REFERENCES materials(id)
    )''')
    
    conn.commit()
    conn.close()

# Initialize database on startup
init_db()

# Helper functions
def get_db():
    conn = sqlite3.connect('intellexa.db')
    conn.row_factory = sqlite3.Row
    return conn

def extract_text_from_pdf(pdf_path):
    """Extract text from PDF file"""
    try:
        reader = PdfReader(pdf_path)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        return text.strip()
    except Exception as e:
        print(f"Error extracting text from PDF: {e}")
        return None

def generate_summary(text, difficulty="standard"):
    """Generate summary using Gemini AI"""
    if not model:
        return "AI service not available. Please configure GOOGLE_API_KEY in .env file."
    
    try:
        difficulty_prompts = {
            'beginner': 'in very simple terms suitable for beginners',
            'standard': 'in a balanced way suitable for most learners',
            'intermediate': 'with detailed explanations for intermediate learners',
            'advanced': 'with technical depth for advanced learners',
            'exam-prep': 'focusing on key concepts for exam preparation'
        }
        
        prompt = f"""Summarize the following text {difficulty_prompts.get(difficulty, difficulty_prompts['standard'])}. 
        Provide a clear, concise summary that captures the main ideas and key concepts.
        
        Text: {text[:8000]}"""
        
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"Error generating summary: {e}")
        return "Error generating summary. Please try again."

def generate_flashcards(text, num_cards=5):
    """Generate flashcards using Gemini AI"""
    print(f"\n--- generate_flashcards() called ---")
    print(f"Text length: {len(text)} characters")
    print(f"Number of cards requested: {num_cards}")
    print(f"Model available: {model is not None}")
    
    if not model:
        print("ERROR: AI model not initialized")
        return []
    
    try:
        print("Creating prompt for AI...")
        prompt = f"""Create {num_cards} ULTRA-CONCISE revision flashcards for quick memorization.

STRICT RULES:
- Questions: SHORT and DIRECT (5-10 words max)
- Answers: EXTREMELY BRIEF
  * Definitions: 1-5 words
  * Facts: 1-3 words  
  * Explanations: MAXIMUM 1 sentence (15 words max)
- Focus ONLY on the most important, testable facts
- Perfect for rapid revision before exams

Format as JSON array with 'question' and 'answer' fields.

GOOD Examples:
[
  {{"question": "What is supervised learning?", "answer": "Learning from labeled data"}},
  {{"question": "Define overfitting", "answer": "Memorizing training data"}},
  {{"question": "What is gradient descent?", "answer": "Optimization algorithm"}},
  {{"question": "Main types of ML?", "answer": "Supervised, unsupervised, reinforcement"}}
]

BAD Examples (TOO LONG):
[
  {{"question": "Can you explain what supervised learning means?", "answer": "Supervised learning is a type of machine learning where the algorithm learns from labeled data, meaning each training example is paired with an output label."}}
]

Text: {text[:8000]}

Return ONLY the JSON array."""
        
        print(f"Sending request to Gemini AI...")
        print(f"Using model: {model._model_name if hasattr(model, '_model_name') else 'Unknown'}")
        
        try:
            response = model.generate_content(
                prompt,
                generation_config={
                    'temperature': 0.7,
                    'max_output_tokens': 4096,  # Increased for more flashcards
                }
            )
            print(f"✓ AI Response received successfully!")
            print(f"Response type: {type(response)}")
            
            # Check if response has text
            if not hasattr(response, 'text'):
                print(f"ERROR: Response has no text attribute")
                print(f"Response object: {dir(response)}")
                return []
            
            response_text = response.text.strip()
            print(f"Response text length: {len(response_text)} characters")
            print(f"Response preview: {response_text[:200]}...")
            
        except Exception as api_error:
            print(f"ERROR calling Gemini API: {api_error}")
            print(f"Error type: {type(api_error).__name__}")
            import traceback
            traceback.print_exc()
            return []
        
        # Extract JSON from response
        print("Extracting JSON from response...")
        
        # Try to find complete JSON array
        json_match = re.search(r'\[\s*{.*?}\s*\]', response_text, re.DOTALL)
        
        if json_match:
            json_str = json_match.group()
            print(f"JSON found. Length: {len(json_str)} characters")
            try:
                flashcards = json.loads(json_str)
                print(f"Successfully parsed {len(flashcards)} flashcards")
                
                # Validate flashcards have required fields
                valid_flashcards = []
                for fc in flashcards:
                    if 'question' in fc and 'answer' in fc:
                        if fc['question'].strip() and fc['answer'].strip():
                            valid_flashcards.append(fc)
                
                print(f"Valid flashcards: {len(valid_flashcards)}")
                return valid_flashcards[:num_cards]
            except json.JSONDecodeError as je:
                print(f"JSON parsing error: {je}")
                print(f"Attempted to parse: {json_str[:500]}...")
                return []
        else:
            print("WARNING: No valid JSON array found in response")
            print(f"Full response (first 1000 chars): {response_text[:1000]}")
            
            # Try alternative extraction - look for individual flashcard objects
            try:
                flashcards = []
                # Find all question-answer pairs
                pairs = re.findall(r'"question"\s*:\s*"([^"]+)"[^}]*"answer"\s*:\s*"([^"]+)"', response_text, re.DOTALL)
                for q, a in pairs[:num_cards]:
                    flashcards.append({'question': q, 'answer': a})
                
                if flashcards:
                    print(f"Extracted {len(flashcards)} flashcards using alternative method")
                    return flashcards
            except Exception as e:
                print(f"Alternative extraction failed: {e}")
            
            return []
    except Exception as e:
        print(f"EXCEPTION in generate_flashcards: {e}")
        import traceback
        traceback.print_exc()
        return []

def generate_quiz(text, num_questions=5):
    """Generate quiz questions using Gemini AI"""
    if not model:
        return []
    
    try:
        prompt = f"""Based on the following text, create {num_questions} multiple choice quiz questions.
        For each question, provide:
        - A clear question
        - 4 answer options
        - The index (0-3) of the correct answer
        
        Format your response as a JSON array with objects containing 'question', 'options' (array of 4 strings), and 'correct' (integer 0-3) fields.
        
        Text: {text[:8000]}
        
        Return ONLY the JSON array, no additional text."""
        
        response = model.generate_content(prompt)
        response_text = response.text.strip()
        
        # Extract JSON from response
        json_match = re.search(r'\[.*\]', response_text, re.DOTALL)
        if json_match:
            quiz = json.loads(json_match.group())
            return quiz[:num_questions]
        else:
            return []
    except Exception as e:
        print(f"Error generating quiz: {e}")
        return []

def get_user_stats(user_id):
    """Get user statistics for dashboard"""
    conn = get_db()
    
    # Count materials
    materials_count = conn.execute('SELECT COUNT(*) FROM materials WHERE user_id = ?', (user_id,)).fetchone()[0]
    
    # Count flashcards
    flashcards_count = conn.execute('''
        SELECT COUNT(*) FROM flashcards f
        JOIN materials m ON f.material_id = m.id
        WHERE m.user_id = ?
    ''', (user_id,)).fetchone()[0]
    
    # Count quiz attempts
    quiz_count = conn.execute('SELECT COUNT(*) FROM quiz_attempts WHERE user_id = ?', (user_id,)).fetchone()[0]
    
    # Calculate average score
    avg_score = conn.execute('''
        SELECT AVG(CAST(score AS FLOAT) / total_questions * 100) 
        FROM quiz_attempts 
        WHERE user_id = ?
    ''', (user_id,)).fetchone()[0]
    
    conn.close()
    
    return {
        'materials_count': materials_count,
        'flashcards_count': flashcards_count,
        'quiz_count': quiz_count,
        'avg_score': round(avg_score, 1) if avg_score else 0
    }

# Routes
@app.route('/')
def home():
    """Landing page"""
    return render_template('landing_page.html')

@app.route('/signin')
def signin():
    """Sign in page"""
    return render_template('signin.html')

@app.route('/signup')
def signup():
    """Sign up page"""
    return render_template('signup.html')

@app.route('/login', methods=['POST'])
def login():
    """Handle login form submission"""
    email = request.form.get('email')
    password = request.form.get('password')
    
    if not email or not password:
        flash('Please fill in all fields', 'error')
        return redirect(url_for('signin'))
    
    try:
        conn = get_db()
        cursor = conn.execute('SELECT id, name, email, password FROM users WHERE email = ?', (email,))
        user = cursor.fetchone()
        conn.close()
        
        if user:
            # Access Row object fields by column name
            user_password = user[3]  # password is the 4th column (index 3)
            print(f"Login attempt for: {email}")
            print(f"Input password: {password}")
            print(f"Password hash type: {type(user_password)}")
            print(f"Password hash from DB: {user_password[:50] if len(user_password) > 50 else user_password}")
            print(f"Password hash length: {len(user_password)}")
            
            # Try password verification
            verification_result = check_password_hash(user_password, password)
            print(f"Password check result: {verification_result}")
            
            if verification_result:
                session['user_id'] = user[0]  # id
                session['user_name'] = user[1]  # name
                session['user_email'] = user[2]  # email
                session['logged_in'] = True
                flash('Successfully logged in!', 'success')
                return redirect(url_for('dashboard'))
            else:
                print("Password check failed - hash verification returned False")
        else:
            print(f"No user found with email: {email}")
        
        flash('Invalid email or password', 'error')
        return redirect(url_for('signin'))
    except Exception as e:
        print(f"Login error: {e}")
        import traceback
        traceback.print_exc()
        flash('An error occurred during login. Please try again.', 'error')
        return redirect(url_for('signin'))

@app.route('/register', methods=['POST'])
def register():
    """Handle registration form submission"""
    name = request.form.get('name')
    email = request.form.get('email')
    password = request.form.get('password')
    
    if not name or not email or not password:
        flash('Please fill in all fields', 'error')
        return redirect(url_for('signup'))
    
    try:
        conn = get_db()
        
        # Check if user already exists
        existing = conn.execute('SELECT id FROM users WHERE email = ?', (email,)).fetchone()
        if existing:
            conn.close()
            flash('Email already registered', 'error')
            return redirect(url_for('signup'))
        
        # Create new user
        hashed_password = generate_password_hash(password)
        print(f"Registration: Hashing password for {email}")
        print(f"Generated hash: {hashed_password[:20]}...")
        
        cursor = conn.execute('INSERT INTO users (name, email, password) VALUES (?, ?, ?)',
                     (name, email, hashed_password))
        conn.commit()
        
        # Get the last inserted user ID
        user_id = cursor.lastrowid
        conn.close()
        
        print(f"User registered successfully with ID: {user_id}")
        
        # Log in the new user
        session['user_id'] = user_id
        session['user_name'] = name
        session['user_email'] = email
        session['logged_in'] = True
        flash('Account created successfully!', 'success')
        return redirect(url_for('dashboard'))
    except Exception as e:
        print(f"Registration error: {e}")
        import traceback
        traceback.print_exc()
        flash('An error occurred during registration. Please try again.', 'error')
        return redirect(url_for('signup'))

@app.route('/dashboard')
def dashboard():
    """User dashboard - main app interface"""
    if not session.get('logged_in'):
        flash('Please log in to access the dashboard', 'error')
        return redirect(url_for('signin'))
    
    user_id = session.get('user_id')
    user_name = session.get('user_name', 'User')
    
    # Get user's study materials
    conn = get_db()
    materials = conn.execute('''
        SELECT * FROM materials 
        WHERE user_id = ? 
        ORDER BY created_at DESC
    ''', (user_id,)).fetchall()
    conn.close()
    
    return render_template('dashboard.html', user_name=user_name, materials=materials)

@app.route('/study/<int:material_id>')
def study_material(material_id):
    """Study material detail page"""
    if not session.get('logged_in'):
        flash('Please log in to access study materials', 'error')
        return redirect(url_for('signin'))
    
    user_id = session.get('user_id')
    user_name = session.get('user_name', 'User')
    
    conn = get_db()
    material = conn.execute('''
        SELECT * FROM materials 
        WHERE id = ? AND user_id = ?
    ''', (material_id, user_id)).fetchone()
    
    # Track activity
    conn.execute('''
        INSERT INTO user_activity (user_id, material_id, activity_type)
        VALUES (?, ?, ?)
    ''', (user_id, material_id, 'view_material'))
    conn.commit()
    conn.close()
    
    if not material:
        flash('Material not found', 'error')
        return redirect(url_for('dashboard'))
    
    return render_template('study_material.html', user_name=user_name, material=material)

@app.route('/flashcards/<int:material_id>')
def flashcards(material_id):
    """Flashcards page"""
    if not session.get('logged_in'):
        flash('Please log in to access flashcards', 'error')
        return redirect(url_for('signin'))
    
    user_id = session.get('user_id')
    user_name = session.get('user_name', 'User')
    
    conn = get_db()
    material = conn.execute('''
        SELECT * FROM materials 
        WHERE id = ? AND user_id = ?
    ''', (material_id, user_id)).fetchone()
    
    flashcards_list = conn.execute('''
        SELECT * FROM flashcards 
        WHERE material_id = ?
    ''', (material_id,)).fetchall()
    
    # Track activity
    conn.execute('''
        INSERT INTO user_activity (user_id, material_id, activity_type)
        VALUES (?, ?, ?)
    ''', (user_id, material_id, 'flashcards'))
    conn.commit()
    conn.close()
    
    if not material:
        flash('Material not found', 'error')
        return redirect(url_for('dashboard'))
    
    return render_template('flashcards.html', 
                         user_name=user_name, 
                         material_id=material_id,
                         material=material,
                         flashcards=flashcards_list)

@app.route('/quiz/<int:material_id>')
def quiz(material_id):
    """Quiz page"""
    if not session.get('logged_in'):
        flash('Please log in to access quizzes', 'error')
        return redirect(url_for('signin'))
    
    user_id = session.get('user_id')
    user_name = session.get('user_name', 'User')
    
    conn = get_db()
    material = conn.execute('''
        SELECT * FROM materials 
        WHERE id = ? AND user_id = ?
    ''', (material_id, user_id)).fetchone()
    
    quiz_questions = conn.execute('''
        SELECT * FROM quizzes 
        WHERE material_id = ?
    ''', (material_id,)).fetchall()
    
    # Track activity (Note: quiz completion is tracked in submit_quiz)
    conn.execute('''
        INSERT INTO user_activity (user_id, material_id, activity_type)
        VALUES (?, ?, ?)
    ''', (user_id, material_id, 'start_quiz'))
    conn.commit()
    conn.close()
    
    if not material:
        flash('Material not found', 'error')
        return redirect(url_for('dashboard'))
    
    return render_template('quiz.html', 
                         user_name=user_name, 
                         material_id=material_id,
                         material=material,
                         quiz_questions=quiz_questions)

@app.route('/growth')
def growth_dashboard():
    """Growth analytics dashboard"""
    if not session.get('logged_in'):
        flash('Please log in to access growth analytics', 'error')
        return redirect(url_for('signin'))
    
    user_id = session.get('user_id')
    user_name = session.get('user_name', 'User')
    
    # Get user statistics and activity
    conn = get_db()
    
    # Weekly activity (last 30 days for better visualization)
    thirty_days_ago = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    weekly_activity_raw = conn.execute('''
        SELECT DATE(created_at) as date, COUNT(*) as count
        FROM user_activity
        WHERE user_id = ? AND created_at >= ?
        GROUP BY DATE(created_at)
        ORDER BY date
    ''', (user_id, thirty_days_ago)).fetchall()
    weekly_activity = [dict(row) for row in weekly_activity_raw]
    
    # Quiz performance over time
    quiz_attempts_raw = conn.execute('''
        SELECT qa.score, qa.total_questions, qa.completed_at, m.title, m.subject
        FROM quiz_attempts qa
        JOIN materials m ON qa.material_id = m.id
        WHERE qa.user_id = ?
        ORDER BY qa.completed_at DESC
        LIMIT 10
    ''', (user_id,)).fetchall()
    quiz_attempts = [dict(row) for row in quiz_attempts_raw]
    
    # Subject distribution with counts
    subject_dist_raw = conn.execute('''
        SELECT subject, COUNT(*) as count
        FROM materials
        WHERE user_id = ?
        GROUP BY subject
        ORDER BY count DESC
    ''', (user_id,)).fetchall()
    subject_dist = [dict(row) for row in subject_dist_raw]
    
    # Study streak (consecutive days with activity)
    recent_activity = conn.execute('''
        SELECT DISTINCT DATE(created_at) as date
        FROM user_activity
        WHERE user_id = ?
        ORDER BY date DESC
        LIMIT 30
    ''', (user_id,)).fetchall()
    
    # Calculate streak
    streak = 0
    if recent_activity:
        today = datetime.now().date()
        for activity in recent_activity:
            activity_date = datetime.strptime(activity['date'], '%Y-%m-%d').date()
            expected_date = today - timedelta(days=streak)
            if activity_date == expected_date:
                streak += 1
            else:
                break
    
    # Activity breakdown by type
    activity_breakdown_raw = conn.execute('''
        SELECT activity_type, COUNT(*) as count
        FROM user_activity
        WHERE user_id = ?
        GROUP BY activity_type
    ''', (user_id,)).fetchall()
    activity_breakdown = [dict(row) for row in activity_breakdown_raw]
    
    # Materials created over time (last 30 days)
    materials_timeline_raw = conn.execute('''
        SELECT DATE(created_at) as date, COUNT(*) as count, subject
        FROM materials
        WHERE user_id = ? AND created_at >= ?
        GROUP BY DATE(created_at), subject
        ORDER BY date DESC
    ''', (user_id, thirty_days_ago)).fetchall()
    materials_timeline = [dict(row) for row in materials_timeline_raw]
    
    conn.close()
    
    stats = get_user_stats(user_id)
    stats['streak'] = streak
    
    return render_template('growth_dashboard.html', 
                         user_name=user_name,
                         stats=stats,
                         weekly_activity=weekly_activity,
                         quiz_attempts=quiz_attempts,
                         subject_dist=subject_dist,
                         activity_breakdown=activity_breakdown,
                         materials_timeline=materials_timeline)

@app.route('/upload', methods=['POST'])
def upload_document():
    """Handle multiple document uploads"""
    if not session.get('logged_in'):
        return jsonify({'error': 'Not authenticated'}), 401
    
    user_id = session.get('user_id')
    
    if 'files' not in request.files:
        return jsonify({'error': 'No files provided'}), 400
    
    files = request.files.getlist('files')
    uploaded_materials = []
    
    for file in files:
        if file.filename == '':
            continue
        
        if file and file.filename.endswith('.pdf'):
            try:
                # Save file
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"{timestamp}_{file.filename}"
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
        
                # Extract text
                text_content = extract_text_from_pdf(filepath)
                if not text_content:
                    continue
                
                # Generate title from filename
                title = file.filename.replace('.pdf', '').replace('_', ' ').title()
                
                # Generate summary
                summary = generate_summary(text_content)
                
                # Detect subject from content
                subject = detect_subject(text_content)
                
                # Save to database
                conn = get_db()
                cursor = conn.execute('''
                    INSERT INTO materials (user_id, title, subject, file_type, file_path, text_content, summary)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (user_id, title, subject, 'pdf', filepath, text_content, summary))
                material_id = cursor.lastrowid
                
                # Generate flashcards
                flashcards_data = generate_flashcards(text_content)
                for fc in flashcards_data:
                    conn.execute('''
                        INSERT INTO flashcards (material_id, question, answer)
                        VALUES (?, ?, ?)
                    ''', (material_id, fc.get('question', ''), fc.get('answer', '')))
                
                # Generate quiz questions
                quiz_data = generate_quiz(text_content)
                for q in quiz_data:
                    conn.execute('''
                        INSERT INTO quizzes (material_id, question, options, correct_answer)
                        VALUES (?, ?, ?, ?)
                    ''', (material_id, q.get('question', ''), json.dumps(q.get('options', [])), q.get('correct', 0)))
                
                # Log activity
                conn.execute('''
                    INSERT INTO user_activity (user_id, material_id, activity_type)
                    VALUES (?, ?, ?)
                ''', (user_id, material_id, 'upload'))
                
                conn.commit()
                conn.close()
                
                uploaded_materials.append({
                    'id': material_id,
                    'title': title,
                    'subject': subject
                })
                
            except Exception as e:
                print(f"Error processing file {file.filename}: {e}")
                continue
    
    if uploaded_materials:
        return jsonify({
            'success': True,
            'message': f'{len(uploaded_materials)} file(s) uploaded successfully',
            'materials': uploaded_materials
        })
    else:
        return jsonify({'error': 'Failed to process files'}), 400

def detect_subject(text):
    """Detect subject from text content using AI"""
    if not model:
        return "General"
    
    try:
        prompt = f"""Based on the following text excerpt, identify the main subject or topic in 1-3 words.
        Examples: "Machine Learning", "Physics", "Mathematics", "History", etc.
        
        Text: {text[:2000]}
        
        Return ONLY the subject name, nothing else."""
        
        response = model.generate_content(prompt)
        subject = response.text.strip()
        return subject if len(subject) < 50 else "General"
    except:
        return "General"

@app.route('/generate_summary', methods=['POST'])
def generate_summary_route():
    """Generate AI summary from uploaded document"""
    if not session.get('logged_in'):
        return jsonify({'error': 'Not authenticated'}), 401
    
    data = request.json
    material_id = data.get('material_id')
    difficulty = data.get('difficulty', 'standard')
    
    conn = get_db()
    material = conn.execute('SELECT text_content FROM materials WHERE id = ?', (material_id,)).fetchone()
    conn.close()
    
    if not material:
        return jsonify({'error': 'Material not found'}), 404
    
    summary = generate_summary(material['text_content'], difficulty)
    
    # Update summary in database
    conn = get_db()
    conn.execute('UPDATE materials SET summary = ? WHERE id = ?', (summary, material_id))
    conn.commit()
    conn.close()
    
    return jsonify({
        'success': True,
        'summary': summary
    })

@app.route('/generate_flashcards_for_material', methods=['POST'])
def generate_flashcards_for_material():
    """Generate flashcards on-demand for a material"""
    print("\n" + "="*80)
    print("FLASHCARD GENERATION REQUEST RECEIVED")
    print("="*80)
    
    if not session.get('logged_in'):
        print("ERROR: User not authenticated")
        return jsonify({'error': 'Not authenticated'}), 401
    
    data = request.json
    material_id = data.get('material_id')
    num_cards = data.get('num_cards', 10)  # Default to 10 if not specified
    print(f"Material ID: {material_id}")
    print(f"Number of cards requested: {num_cards}")
    
    if not material_id:
        print("ERROR: No material ID provided")
        return jsonify({'error': 'Material ID required'}), 400
    
    try:
        print("Connecting to database...")
        conn = get_db()
        
        # Get material text content
        print(f"Fetching material {material_id} from database...")
        material = conn.execute('SELECT text_content FROM materials WHERE id = ?', (material_id,)).fetchone()
        
        if not material:
            print(f"ERROR: Material {material_id} not found in database")
            conn.close()
            return jsonify({'error': 'Material not found'}), 404
        
        text_content = material[0]
        print(f"Material found. Text length: {len(text_content)} characters")
        
        # Generate flashcards
        print("Calling AI to generate flashcards...")
        print(f"AI Model available: {model is not None}")
        
        flashcards_data = generate_flashcards(text_content, num_cards=num_cards)
        
        print(f"AI returned {len(flashcards_data) if flashcards_data else 0} flashcards")
        
        if not flashcards_data:
            print("ERROR: No flashcards generated by AI")
            conn.close()
            return jsonify({'error': 'Failed to generate flashcards'}), 500
        
        # Delete existing flashcards for this material
        print(f"Deleting existing flashcards for material {material_id}...")
        conn.execute('DELETE FROM flashcards WHERE material_id = ?', (material_id,))
        
        # Save new flashcards to database
        print(f"Saving {len(flashcards_data)} new flashcards to database...")
        for idx, fc in enumerate(flashcards_data):
            print(f"  Saving flashcard {idx+1}: {fc.get('question', 'N/A')[:50]}...")
            conn.execute('''
                INSERT INTO flashcards (material_id, question, answer)
                VALUES (?, ?, ?)
            ''', (material_id, fc.get('question', ''), fc.get('answer', '')))
        
        conn.commit()
        conn.close()
        
        print(f"SUCCESS: {len(flashcards_data)} flashcards saved successfully!")
        print("="*80 + "\n")
        
        return jsonify({
            'success': True,
            'flashcards': flashcards_data,
            'message': f'{len(flashcards_data)} flashcards generated successfully'
        })
        
    except Exception as e:
        print(f"EXCEPTION in generate_flashcards_for_material: {e}")
        import traceback
        traceback.print_exc()
        print("="*80 + "\n")
        return jsonify({'error': str(e)}), 500

@app.route('/generate_quiz_for_material', methods=['POST'])
def generate_quiz_for_material():
    """Generate quiz questions on-demand for a material"""
    if not session.get('logged_in'):
        return jsonify({'error': 'Not authenticated'}), 401
    
    data = request.json
    material_id = data.get('material_id')
    num_questions = data.get('num_questions', 10)  # Default to 10 if not specified
    
    if not material_id:
        return jsonify({'error': 'Material ID required'}), 400
    
    try:
        conn = get_db()
        
        # Get material text content
        material = conn.execute('SELECT text_content FROM materials WHERE id = ?', (material_id,)).fetchone()
        
        if not material:
            conn.close()
            return jsonify({'error': 'Material not found'}), 404
        
        text_content = material[0]
        
        # Generate quiz questions
        quiz_data = generate_quiz(text_content, num_questions=num_questions)
        
        if not quiz_data:
            conn.close()
            return jsonify({'error': 'Failed to generate quiz questions'}), 500
        
        # Delete existing quiz questions for this material
        print(f"Deleting existing quiz questions for material {material_id}...")
        conn.execute('DELETE FROM quizzes WHERE material_id = ?', (material_id,))
        
        # Save new quiz questions to database
        print(f"Saving {len(quiz_data)} new quiz questions to database...")
        for q in quiz_data:
            conn.execute('''
                INSERT INTO quizzes (material_id, question, options, correct_answer)
                VALUES (?, ?, ?, ?)
            ''', (material_id, q.get('question', ''), json.dumps(q.get('options', [])), q.get('correct', 0)))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'quiz': quiz_data,
            'message': f'{len(quiz_data)} quiz questions generated successfully'
        })
        
    except Exception as e:
        print(f"Error generating quiz: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/submit_quiz', methods=['POST'])
def submit_quiz():
    """Submit quiz and save score"""
    if not session.get('logged_in'):
        return jsonify({'error': 'Not authenticated'}), 401
    
    user_id = session.get('user_id')
    data = request.json
    material_id = data.get('material_id')
    answers = data.get('answers', {})
    
    conn = get_db()
    quiz_questions = conn.execute('''
        SELECT id, correct_answer FROM quizzes WHERE material_id = ?
    ''', (material_id,)).fetchall()
    
    # Calculate score
    correct = 0
    for q in quiz_questions:
        user_answer = answers.get(str(q['id']))
        if user_answer is not None and int(user_answer) == q['correct_answer']:
            correct += 1
    
    total = len(quiz_questions)
    
    # Save attempt
    conn.execute('''
        INSERT INTO quiz_attempts (user_id, material_id, score, total_questions)
        VALUES (?, ?, ?, ?)
    ''', (user_id, material_id, correct, total))
    
    # Log activity
    conn.execute('''
        INSERT INTO user_activity (user_id, material_id, activity_type)
        VALUES (?, ?, ?)
    ''', (user_id, material_id, 'quiz'))
    
    conn.commit()
    conn.close()
    
    return jsonify({
        'success': True,
        'score': correct,
        'total': total,
        'percentage': round((correct / total * 100) if total > 0 else 0, 1)
    })

@app.route('/chat', methods=['POST'])
def ai_chat():
    """Handle AI chat requests"""
    if not session.get('logged_in'):
        return jsonify({'error': 'Not authenticated'}), 401
    
    if not model:
        return jsonify({'error': 'AI service not available'}), 503
    
    message = request.json.get('message', '')
    material_id = request.json.get('material_id')
    
    if not message:
        return jsonify({'error': 'No message provided'}), 400
    
    # Get material context if provided
    context = ""
    if material_id:
        conn = get_db()
        material = conn.execute('SELECT text_content FROM materials WHERE id = ?', (material_id,)).fetchone()
        conn.close()
        if material:
            context = material['text_content'][:4000]
    
    try:
        if context:
            prompt = f"""Based on the following study material, answer the student's question:
            
Material: {context}

Question: {message}

Provide a clear, helpful answer."""
        else:
            prompt = f"Answer this student's question: {message}"
        
        response = model.generate_content(prompt)
        
        return jsonify({
            'success': True,
            'response': response.text
        })
    except Exception as e:
        print(f"Error in chat: {e}")
        return jsonify({'error': 'Failed to generate response'}), 500

@app.route('/logout')
def logout():
    """Logout user"""
    session.clear()
    flash('You have been logged out successfully', 'info')
    return redirect(url_for('home'))

@app.route('/profile')
def profile():
    """User profile page"""
    if not session.get('logged_in'):
        flash('Please log in to access your profile', 'error')
        return redirect(url_for('signin'))
    
    user_id = session.get('user_id')
    user_name = session.get('user_name', 'User')
    user_email = session.get('user_email', 'user@example.com')
    
    stats = get_user_stats(user_id)
    
    return render_template('profile.html', 
                         user_name=user_name, 
                         user_email=user_email,
                         stats=stats)

@app.route('/settings')
def settings():
    """User settings page"""
    if not session.get('logged_in'):
        flash('Please log in to access settings', 'error')
        return redirect(url_for('signin'))
    
    return render_template('settings.html')

@app.route('/delete_material/<int:material_id>', methods=['POST'])
def delete_material(material_id):
    """Delete a study material"""
    if not session.get('logged_in'):
        return jsonify({'error': 'Not authenticated'}), 401
    
    user_id = session.get('user_id')
    
    conn = get_db()
    material = conn.execute('SELECT * FROM materials WHERE id = ? AND user_id = ?', 
                          (material_id, user_id)).fetchone()
    
    if not material:
        conn.close()
        return jsonify({'error': 'Material not found'}), 404
    
    # Delete file
    if material['file_path'] and os.path.exists(material['file_path']):
        os.remove(material['file_path'])
    
    # Delete from database (cascade will handle related records)
    conn.execute('DELETE FROM flashcards WHERE material_id = ?', (material_id,))
    conn.execute('DELETE FROM quizzes WHERE material_id = ?', (material_id,))
    conn.execute('DELETE FROM quiz_attempts WHERE material_id = ?', (material_id,))
    conn.execute('DELETE FROM user_activity WHERE material_id = ?', (material_id,))
    conn.execute('DELETE FROM materials WHERE id = ?', (material_id,))
    conn.commit()
    conn.close()
    
    return jsonify({'success': True})

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('500.html'), 500

# Template filters
@app.template_filter('datetime')
def datetime_filter(timestamp):
    """Format datetime for templates"""
    if isinstance(timestamp, str):
        dt = datetime.fromisoformat(timestamp)
    else:
        dt = timestamp
    
    now = datetime.now()
    diff = now - dt
    
    if diff.days == 0:
        if diff.seconds < 3600:
            return f"{diff.seconds // 60} minutes ago"
        return f"{diff.seconds // 3600} hours ago"
    elif diff.days == 1:
        return "Yesterday"
    elif diff.days < 7:
        return f"{diff.days} days ago"
    else:
        return dt.strftime('%B %d, %Y')

if __name__ == '__main__':
    # Development server
    app.run(debug=True, host='0.0.0.0', port=5000)
