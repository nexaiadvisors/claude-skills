# Setup (one time, about 10 minutes)

## 1. Python packages
```bash
python3 -m pip install --user opencv-python numpy
```

## 2. An API key (you need at least one)
- **OpenAI (GPT Image), recommended:** create a key at https://platform.openai.com/api-keys. Image
  generation needs a paid API balance (separate from a ChatGPT Plus subscription), and some
  accounts must verify their organization before image models unlock.
- **Google Gemini (Nano Banana Pro):** create a key at https://aistudio.google.com/apikey. Image
  generation needs billing turned on for that Google Cloud project.

Cost per image is about \$0.07 (GPT) and \$0.13 (Gemini) as of November 2026. The default run of
8 shots on both engines is about \$1.65, at most \$3.30 with retries, so it stops at the \$3 cap
unless you agree to more.

## 3. Put the key in the key file
Create the file `~/.config/expression-bank/.env` (on Windows: `%USERPROFILE%\.config\expression-bank\.env`)
with one or both lines:
```
OPENAI_API_KEY=sk-...
GEMINI_API_KEY=AIza...
```
Then lock it so only you can read it (macOS/Linux):
```bash
chmod 600 ~/.config/expression-bank/.env
```
Never paste a key into a chat, a post or a shared folder. The skill reads the file itself and never
prints the key. Keys set in your shell environment override the file. Another file path can be set with
`EXPRESSION_BANK_ENV=/path/to/.env`.

## 4. Check it
```bash
python3 -I scripts/expression_bank.py setup
```
It reports which keys are set (never their values), downloads the two face models once and prints
`SETUP OK`.

## Good reference photos
Give 3-12 photos of the same person. The best references:
- face large and sharp (at least 200 pixels tall; a phone photo from arm's length is plenty)
- facing the camera or close to it, eyes visible, no sunglasses or hands over the face
- one person in the photo (people far in the background are fine)
- normal lighting, no heavy filters or beauty apps
- a mix of days and outfits, so the model learns the face, not one photo

AI headshots (Secta, Aragon and similar) work if they look like you; the check compares every photo
with the others and flags any that look like a different person.
