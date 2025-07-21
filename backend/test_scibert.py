#!/usr/bin/env python3

from scibert_classifier import predict_department_scibert
import json

# Test with the exact text that was passed to SciBERT
test_text = 'obstetrics gynecology reproductive medicine obstetrics gynecology reproductive medicine obstetrics gynecology reproductive medicine obstetrics gynecology reproductive medicine'
print(f'Testing SciBERT with: {test_text[:100]}...')

result = predict_department_scibert(test_text)
print(f'SciBERT result: {result}')

# Also test individual terms
terms = ['obstetrics', 'gynecology', 'reproductive medicine', 'pregnancy', 'maternal', 'placental']
for term in terms:
    result = predict_department_scibert(term)
    print(f'Term "{term}": {result}')

# Test with some research titles from the ORCID data
titles = [
    'Discrete placental gene expression signatures accompany diabetic disease classifications during pregnancy',
    'Fetal sex and the development of gestational diabetes mellitus in gravidae with multiple gestation pregnancies',
    'Obstructive Sleep Apnea and Risk of Miscarriage',
    'Pregnancy and Lactation in a 67-Year-Old Elderly Gravida following Donor Oocyte In Vitro Fertilization'
]

for title in titles:
    result = predict_department_scibert(title)
    print(f'Title "{title[:50]}...": {result}')
