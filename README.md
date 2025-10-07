# Intellexa - AI-Powered Study Platform

A modern web application built with Flask that transforms study materials into AI-powered summaries, flashcards, quizzes, and interactive learning tools.

## Features

- 🏠 **Landing Page** - Modern, responsive design showcasing the platform
- 🔐 **Authentication** - User registration and login system
- 📊 **Dashboard** - Main interface for uploading and processing documents
- 🤖 **AI Features**:
  - Smart document summaries
  - Interactive flashcards generation
  - Adaptive quiz creation
  - AI chat assistant for Q&A
- 👤 **User Profile** - View user statistics and progress
- ⚙️ **Settings** - Customize AI preferences and privacy settings

## Project Structure

```
student/
├── app.py                 # Main Flask application
├── requirements.txt       # Python dependencies
├── README.md             # This file
├── templates/            # HTML templates
│   ├── landing_page.html
│   ├── signin.html
│   ├── signup.html
│   ├── dashboard.html
│   ├── profile.html
│   ├── settings.html
│   ├── 404.html
│   └── 500.html
├── static/               # Static files (CSS, JS, images)
└── uploads/              # File upload directory (created automatically)
```

## Installation & Setup

### 1. Clone or Download the Project
Make sure you have all the files in your project directory.

### 2. Install Python Dependencies
```bash
pip install -r requirements.txt
```

### 3. Set Up Environment Variables
Create a `.env` file in the project root:
```bash
GOOGLE_API_KEY=your_gemini_api_key_here
```

**To get your Gemini API key:**
1. Visit [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Sign in with your Google account
3. Create a new API key
4. Copy and paste it into your `.env` file

### 4. Run the Application
```bash
python app.py
```

The application will automatically:
- Create a SQLite database (`intellexa.db`)
- Set up all required tables
- Initialize the uploads directory

### 5. Access the Application
Open your web browser and go to: `http://localhost:5000`

## Usage

### Getting Started
1. **Visit the Landing Page** - Browse features and learn about Intellexa
2. **Sign Up** - Create a new account (password is securely hashed)
3. **Upload PDFs** - Click "Upload New" to open the upload modal
4. **Multiple Uploads** - Select or drag & drop multiple PDF files at once
5. **AI Processing** - Wait while AI generates summaries, flashcards, and quizzes
6. **Study** - Review your materials with AI-generated content

### Features Overview

#### Dashboard
- **Upload Multiple PDFs**: Beautiful modal with drag & drop support
- **Real-time Processing**: AI extracts text and generates content automatically
- **Subject Detection**: AI automatically categorizes your materials
- **Material Cards**: See all your uploaded materials with summaries

#### Study Materials
- **AI Summaries**: Generated based on your selected difficulty level
- **Dynamic Generation**: Regenerate summaries in different styles (Beginner, Intermediate, Advanced, Exam Prep)
- **Flashcards**: AI-generated Q&A for active recall
- **Quizzes**: Multiple-choice questions with score tracking
- **AI Chat**: Ask questions about your study material

#### Profile & Analytics
- **Real Statistics**: See actual upload counts, flashcard numbers, quiz scores
- **Growth Dashboard**: Track your learning progress over time
- **Quiz History**: View all your quiz attempts and scores

## API Endpoints

### Public Routes
- `GET /` - Landing page
- `GET /signin` - Sign in page
- `GET /signup` - Sign up page
- `POST /login` - Handle login (with database authentication)
- `POST /register` - Handle registration (with password hashing)

### Protected Routes (require authentication)
- `GET /dashboard` - User dashboard with uploaded materials
- `GET /study/<id>` - Study material detail page
- `GET /flashcards/<id>` - Flashcards for a material
- `GET /quiz/<id>` - Quiz for a material
- `GET /growth` - Growth analytics dashboard
- `GET /profile` - User profile with statistics
- `GET /settings` - User settings
- `GET /logout` - Logout user

### API Endpoints
- `POST /upload` - Upload multiple PDFs and process with AI
- `POST /generate_summary` - Generate/regenerate AI summary with difficulty level
- `POST /submit_quiz` - Submit quiz answers and save score
- `POST /chat` - AI chat interaction with context
- `POST /delete_material/<id>` - Delete a study material

## Technology Stack

- **Backend**: Flask (Python web framework)
- **Database**: SQLite (with proper schema and relationships)
- **AI**: Google Gemini Pro (for content generation)
- **PDF Processing**: PyPDF (text extraction)
- **Authentication**: Werkzeug (password hashing)
- **Frontend**: HTML5, CSS3, JavaScript
- **Styling**: Custom CSS with Inter font family
- **Icons**: Font Awesome
- **Charts**: Chart.js (for growth dashboard)

## Key Features

### ✅ Implemented
- ✨ Real AI content generation using Gemini API
- 🗄️ Full SQLite database with proper relationships
- 🔐 Secure authentication with password hashing
- 📄 Multiple PDF upload with modal interface
- 🎯 Auto-generated summaries, flashcards, and quizzes
- 📊 Real-time progress tracking and statistics
- 💬 AI chat assistant for Q&A
- 📈 Growth analytics dashboard
- 🎨 Beautiful, responsive UI with animations

### Future Enhancements
- 📧 Email notifications and reminders
- 🤝 Study groups and social features
- 🎯 Spaced repetition algorithm
- 📱 Mobile app version
- 🌍 Multi-language support
- 🎓 Export to PDF/print options

## Security Considerations

- Change the secret key in production
- Implement proper password hashing
- Add CSRF protection
- Validate file uploads
- Use HTTPS in production
- Implement rate limiting

## Browser Compatibility

- Chrome (recommended)
- Firefox
- Safari
- Edge
- Mobile browsers

## Troubleshooting

### Common Issues

1. **"GOOGLE_API_KEY not found" warning**
   - Make sure you created a `.env` file in the project root
   - Add your Gemini API key: `GOOGLE_API_KEY=your_key_here`
   - Restart the application after creating the file

2. **Port 5000 already in use**
   ```bash
   # Edit app.py and change the port
   app.run(debug=True, host='0.0.0.0', port=5001)
   ```

3. **Module not found errors**
   ```bash
   # Reinstall dependencies
   pip install -r requirements.txt
   ```

4. **PDF text extraction fails**
   - Ensure PDFs contain actual text (not just images)
   - Some PDFs may be scanned images and won't work
   - Try with a different PDF file

5. **AI generation is slow**
   - This is normal for the first request
   - Gemini API may take 10-30 seconds per PDF
   - Larger PDFs take longer to process

6. **Database locked error**
   - Close any other instances of the application
   - Delete `intellexa.db` and restart (will lose data)

### Getting Help

If you encounter issues:
1. Check the terminal/console for error messages
2. Ensure your `.env` file is configured correctly
3. Verify your Gemini API key is valid
4. Try with a simple, text-based PDF first

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is for educational and demonstration purposes.

## Support

For questions or issues, please check the troubleshooting section or create an issue in the repository.

---

**Intellexa** - Learn smarter, not harder! 🧠✨
