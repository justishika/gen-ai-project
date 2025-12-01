# NER (Named Entity Recognition) Setup Guide

This project uses spaCy for Named Entity Recognition. You need to download the spaCy English model before using the NER features.

## Installation Steps

### 1. Install spaCy (if not already installed)
```bash
pip install spacy
```

### 2. Download the English Model
```bash
python -m spacy download en_core_web_sm
```

This will download the small English model (~15MB) which includes:
- Named Entity Recognition
- Part-of-speech tagging
- Dependency parsing
- Word vectors

### 3. Verify Installation
You can verify the installation by running:
```bash
python -c "import spacy; nlp = spacy.load('en_core_web_sm'); print('Model loaded successfully!')"
```

## Alternative: Larger Model (Better Accuracy)

If you want better accuracy, you can download the larger model:
```bash
python -m spacy download en_core_web_lg
```

Then update `ner_extractor.py` line 20 to use:
```python
nlp_model = spacy.load("en_core_web_lg")
```

**Note:** The large model is ~500MB, so it takes longer to download and uses more memory.

## Troubleshooting

### Error: "Model 'en_core_web_sm' not found"
- Make sure you've run: `python -m spacy download en_core_web_sm`
- Verify you're using the same Python environment where you installed spaCy

### Error: "No module named 'spacy'"
- Install spaCy: `pip install spacy`
- Make sure you're in the correct virtual environment

### Model Download Fails
- Check your internet connection
- Try downloading manually from: https://github.com/explosion/spacy-models/releases
- Or use: `python -m spacy download en_core_web_sm --direct`

## Features Enabled

Once the model is installed, the NER feature will extract:
- **People** (PERSON)
- **Organizations** (ORG)
- **Locations** (GPE, LOC)
- **Dates** (DATE)
- **Times** (TIME)
- **Money** (MONEY)
- **Percentages** (PERCENT)
- **Events** (EVENT)
- **Products** (PRODUCT)
- **Laws** (LAW)
- **Languages** (LANGUAGE)
- **Groups** (NORP)

Plus:
- Timeline extraction
- Key facts and statistics
- Relationship mapping between entities

