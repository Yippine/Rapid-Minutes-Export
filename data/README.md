# Data Directory Structure

This directory contains all data files used by the Rapid Minutes Export system.

## Directory Structure

### 📁 input/
Input files directory - Contains uploaded meeting transcription files
- **Purpose**: Store user-uploaded text files awaiting processing
- **File Types**: .txt files containing meeting transcriptions
- **Retention**: Files are kept for reference and backup purposes

### 📁 output/
Output files directory - Contains generated meeting minutes
- **Purpose**: Store processed Word and PDF meeting minutes
- **File Types**: .docx and .pdf files
- **Retention**: Generated files available for download

### 📁 temp/
Temporary processing directory - Contains intermediate processing files
- **Purpose**: Store temporary files during AI processing and document generation
- **File Types**: Various temporary formats
- **Retention**: Files are automatically cleaned up after processing

## Usage Notes

- Input files should be in UTF-8 text format for best processing results
- Output files are organized by timestamp and processing ID
- Temp directory is automatically managed by the system
- All directories support concurrent access for multi-user scenarios

## File Naming Convention

- **Input**: `{timestamp}_{original_filename}.txt`
- **Output**: `{timestamp}_meeting_minutes.{docx|pdf}`
- **Temp**: `{process_id}_{stage}_{filename}`