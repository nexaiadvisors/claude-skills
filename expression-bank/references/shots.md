# Custom shots

Pass `--shots <file>` with a JSON list. Each shot needs `id` (a short name, used as the file name) and
`expression` (what the face and hands do). `clothes` and `background` are optional; vary them so the
bank does not look like one photo session.

```json
[
  {"id": "thinking", "expression": "thoughtful, looking slightly up and to the side, one finger tapping the chin",
   "clothes": "a light blue denim shirt", "background": "a home office with shelves"},
  {"id": "laughing", "expression": "laughing out loud, eyes crinkled, head tilted back slightly",
   "clothes": "a heather grey t-shirt", "background": "a sunny cafe"}
]
```

Tips from the first runs:
- Describe the face and the hands, not a feeling alone: "eyebrows high, mouth open, palms on cheeks"
  beats "surprised".
- Keep the face large: head and shoulders. Faces far from the camera drift the most.
- Covering much of the face (a hand over the forehead, head down on a desk) lowers the score and
  can fail; expect REVIEW there and look by eye.
- Leave space and props blank (a blank phone screen, a plain wall) and add real text or screens
  later in your design tool. Models draw text as nonsense.
