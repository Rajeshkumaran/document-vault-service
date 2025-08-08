# Firebase Setup Guide

## Migration from Supabase to Firebase

This application has been migrated from Supabase to Firebase. Here's how to set it up:

### 1. Firebase Project Setup

1. Go to [Firebase Console](https://console.firebase.google.com/)
2. Create a new project or select an existing one
3. Enable Firestore Database
4. Enable Cloud Storage
5. Create a service account and download the JSON credentials file

### 2. Environment Variables

Create or update your `.env` file with the following Firebase configuration:

```env
# Firebase Configuration
FIREBASE_PROJECT_ID=your-firebase-project-id
FIREBASE_STORAGE_BUCKET=your-project-id.appspot.com
FIREBASE_CREDENTIALS_PATH=/path/to/your/service-account-key.json

# Optional: for production, you can use Application Default Credentials instead of FIREBASE_CREDENTIALS_PATH
```

### 3. Firestore Security Rules (for development)

In the Firebase Console > Firestore Database > Rules, set up basic rules:

```javascript
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    // Allow read/write access to documents collection
    match /documents/{document} {
      allow read, write: if true; // Restrict this in production
    }
  }
}
```

### 4. Cloud Storage Rules (for development)

In the Firebase Console > Storage > Rules:

```javascript
rules_version = '2';
service firebase.storage {
  match /b/{bucket}/o {
    match /{allPaths=**} {
      allow read, write: if true; // Restrict this in production
    }
  }
}
```

### 5. Key Changes from Supabase

- **Database**: PostgreSQL → Firestore (NoSQL)
- **Storage**: Supabase Storage → Cloud Storage
- **Authentication**: Not implemented in this migration (was using Supabase auth)
- **Document IDs**: Now use string IDs instead of integer auto-increment
- **Timestamps**: Use Python datetime objects directly (Firestore handles serialization)

### 6. Testing

Once configured, you can test the API endpoints:

```bash
# Single file upload
curl -X POST "http://localhost:8000/documents/create" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@test.pdf"

# Multiple file upload
curl -X POST "http://localhost:8000/documents/batch" \
  -H "Content-Type: multipart/form-data" \
  -F "files=@test1.pdf" \
  -F "files=@test2.pdf"
```

### 7. Production Considerations

- Use IAM roles instead of service account JSON files
- Implement proper Firestore security rules
- Set up Cloud Storage bucket policies
- Consider implementing Firebase Authentication
- Set up monitoring and logging
