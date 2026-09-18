# I-FNE — Image-based Food Nutrition Estimation

Upload a photo of a meal and get an estimate of its calories and macronutrients:
Ultralytics SAM3 segments the plate into individual foods and a YOLO depth model
estimates each portion.

Rather than trusting the model, it shows you every detected food as a crop to
confirm, re-label, or discard before the nutrition is calculated — built with
FastAPI, React, PostgreSQL and Supabase.
