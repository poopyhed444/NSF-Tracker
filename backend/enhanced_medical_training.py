#!/usr/bin/env python3
"""
Enhanced Training Data Builder with Medical Specialties
Creates comprehensive training data including medical departments like OB/GYN
"""

import json
import random
from pathlib import Path
from typing import List, Tuple, Dict


class MedicalTrainingDataBuilder:
    def __init__(self):
        self.base_dir = Path(__file__).parent
        
    def create_medical_training_data(self) -> Dict:
        """Create comprehensive training data including medical specialties."""
        
        # Enhanced department patterns including medical specialties
        medical_departments = {
            "Obstetrics and Gynecology": [
                "maternal fetal medicine pregnancy complications gestational diabetes",
                "placental development prenatal diagnosis genetic screening",
                "reproductive endocrinology fertility treatment IVF",
                "gynecologic oncology cervical ovarian endometrial cancer",
                "perinatal medicine neonatal outcomes high risk pregnancy",
                "obstetric anesthesia cesarean delivery labor management",
                "contraception family planning reproductive health",
                "maternal mortality postpartum hemorrhage preeclampsia",
                "fetal development intrauterine growth restriction",
                "menopause hormone replacement therapy estrogen",
                "American Journal of Obstetrics and Gynecology",
                "placental gene expression signatures diabetic pregnancy",
                "maternal western diet offspring skeletal muscle",
                "Zika virus microRNA networks placental niches",
                "bronchoalveolar lavage fluid metatranscriptomes COVID",
                "obstructive sleep apnea risk miscarriage pregnancy"
            ],
            "Pediatrics": [
                "child development pediatric medicine adolescent health",
                "neonatal intensive care premature infants NICU",
                "pediatric oncology childhood cancer leukemia treatment",
                "developmental disorders autism spectrum ADHD",
                "pediatric cardiology congenital heart disease",
                "childhood obesity metabolic syndrome diabetes",
                "pediatric surgery minimally invasive laparoscopic",
                "vaccine research immunization programs pediatric",
                "pediatric emergency medicine trauma resuscitation",
                "growth disorders endocrine pediatric hormones"
            ],
            "Cardiology": [
                "coronary artery disease interventional cardiology angioplasty",
                "heart failure cardiac transplantation ventricular assist",
                "arrhythmia electrophysiology pacemaker defibrillator therapy",
                "echocardiography cardiac imaging MRI catheterization",
                "preventive cardiology cardiovascular risk hypertension",
                "cardiac rehabilitation exercise physiology fitness",
                "valve disease mitral aortic stenosis regurgitation",
                "atherosclerosis plaque rupture myocardial infarction",
                "cardiac catheterization stenting balloon angioplasty"
            ],
            "Oncology": [
                "cancer immunotherapy checkpoint inhibitors PD-1 CTLA-4",
                "radiation oncology stereotactic radiosurgery IMRT",
                "tumor biology metastasis invasion angiogenesis",
                "chemotherapy drug resistance mechanisms apoptosis",
                "precision medicine genomic profiling targeted therapy",
                "hematologic malignancies leukemia lymphoma myeloma",
                "solid tumor breast lung colorectal prostate cancer",
                "palliative care symptom management end-of-life",
                "cancer prevention screening mammography colonoscopy"
            ],
            "Dermatology": [
                "melanoma skin cancer dermatopathology mohs surgery",
                "psoriasis inflammatory skin disease biologics",
                "dermatitis eczema atopic allergic contact",
                "cosmetic dermatology laser resurfacing botox",
                "pediatric dermatology congenital skin disorders",
                "dermoscopy skin lesion diagnosis imaging",
                "wound healing tissue repair regenerative medicine",
                "hair disorders alopecia follicle transplantation"
            ],
            "Psychiatry": [
                "depression anxiety mood disorders antidepressants",
                "schizophrenia psychosis antipsychotic medications",
                "bipolar disorder lithium mood stabilizers",
                "PTSD trauma therapy cognitive behavioral",
                "addiction substance abuse rehabilitation treatment",
                "child adolescent psychiatry developmental disorders",
                "neuropsychiatry dementia Alzheimer cognitive decline",
                "suicide prevention crisis intervention mental health"
            ],
            "Orthopedics": [
                "joint replacement knee hip arthritis surgery",
                "sports medicine ACL reconstruction shoulder repair",
                "spine surgery disc herniation spinal fusion",
                "fracture treatment trauma orthopedic fixation",
                "arthroscopy minimally invasive joint surgery",
                "bone healing osteoporosis calcium metabolism",
                "pediatric orthopedics scoliosis developmental dysplasia",
                "hand surgery nerve repair tendon reconstruction"
            ],
            "Neurology": [
                "stroke cerebrovascular disease thrombolysis",
                "epilepsy seizure disorders anticonvulsant therapy",
                "multiple sclerosis demyelinating disease immunotherapy",
                "Parkinson disease movement disorders deep brain stimulation",
                "Alzheimer dementia cognitive impairment memory",
                "headache migraine cluster tension type",
                "neuromuscular disorders myasthenia gravis ALS",
                "brain tumor glioblastoma neuro-oncology surgery"
            ],
            "Anesthesiology": [
                "general anesthesia volatile agents propofol",
                "regional anesthesia spinal epidural nerve blocks",
                "cardiac anesthesia bypass surgery TEE monitoring",
                "pediatric anesthesia congenital heart disease",
                "obstetric anesthesia cesarean labor epidural",
                "pain medicine chronic pain management opioids",
                "critical care intensive care unit ventilation",
                "perioperative medicine enhanced recovery protocols"
            ],
            "Radiology": [
                "diagnostic imaging CT MRI ultrasound mammography",
                "interventional radiology angiography embolization",
                "nuclear medicine PET SPECT radiopharmaceuticals",
                "radiation therapy treatment planning dosimetry",
                "breast imaging mammography tomosynthesis screening",
                "cardiac imaging echocardiography CT angiography",
                "neuroradiology brain MRI stroke imaging",
                "musculoskeletal imaging sports injuries fractures"
            ],
            "Pathology": [
                "surgical pathology biopsy diagnosis histopathology",
                "cytopathology Pap smear fine needle aspiration",
                "hematopathology blood disorders leukemia lymphoma",
                "molecular pathology genetic testing biomarkers",
                "forensic pathology autopsy cause of death",
                "clinical pathology laboratory medicine biochemistry",
                "immunopathology autoimmune disease markers",
                "neuropathology brain biopsy neurodegenerative disease"
            ],
            "Biology": [
                "cell biology molecular genetics cancer research",
                "developmental biology stem cells embryonic",
                "microbiology bacterial viral infectious disease",
                "immunology autoimmune inflammatory response",
                "ecology evolution biodiversity conservation",
                "structural biology protein crystallography",
                "biochemistry enzyme kinetics metabolism",
                "genetics genomics DNA sequencing analysis",
                "neurobiology synaptic plasticity memory"
            ],
            "Chemistry": [
                "organic synthesis catalysis pharmaceutical development",
                "inorganic materials nanochemistry quantum dots",
                "analytical spectroscopy mass spectrometry chromatography",
                "physical chemistry thermodynamics kinetics",
                "medicinal chemistry drug discovery optimization",
                "polymer science macromolecules synthetic methods",
                "computational chemistry molecular modeling",
                "electrochemistry batteries fuel cells energy",
                "chemical biology bioconjugation protein modification"
            ],
            "Physics": [
                "quantum mechanics condensed matter theory",
                "particle physics high energy accelerators",
                "astrophysics cosmology dark matter galaxies",
                "optics lasers photonics optical systems",
                "nuclear physics radioactivity radiation",
                "solid state semiconductors superconductors",
                "plasma physics fusion magnetic confinement",
                "theoretical physics relativity field theory",
                "experimental physics instrumentation detectors"
            ],
            "Computer Science": [
                "machine learning artificial intelligence neural networks",
                "database systems distributed computing cloud",
                "computer graphics visualization rendering",
                "cybersecurity cryptography network security",
                "software engineering programming languages",
                "human computer interaction user interface",
                "algorithms complexity computational theory",
                "computer vision image processing recognition",
                "natural language processing text mining"
            ],
            "Engineering": [
                "biomedical engineering medical devices implants",
                "electrical engineering circuits signal processing",
                "mechanical engineering thermodynamics fluid mechanics",
                "chemical engineering process design optimization",
                "civil engineering structures materials construction",
                "aerospace engineering aircraft spacecraft design",
                "environmental engineering water treatment pollution",
                "materials engineering composites metallurgy",
                "computer engineering embedded systems VLSI"
            ],
            "Mathematics": [
                "pure mathematics algebra topology geometry",
                "applied mathematics differential equations modeling",
                "statistics probability data analysis",
                "computational mathematics numerical methods",
                "optimization operations research algorithms",
                "mathematical biology population dynamics",
                "financial mathematics quantitative analysis",
                "cryptography number theory security",
                "graph theory combinatorics discrete mathematics"
            ],
            "Psychology": [
                "cognitive psychology memory attention perception",
                "developmental psychology child development learning",
                "social psychology group behavior attitudes",
                "clinical psychology therapy mental health",
                "behavioral psychology conditioning learning",
                "neuropsychology brain behavior cognition",
                "personality psychology individual differences",
                "experimental psychology research methodology",
                "educational psychology learning instruction"
            ],
            "Neuroscience": [
                "systems neuroscience neural circuits behavior",
                "molecular neuroscience synaptic transmission",
                "cognitive neuroscience brain imaging fMRI",
                "developmental neuroscience neural development",
                "computational neuroscience neural modeling",
                "behavioral neuroscience animal models",
                "clinical neuroscience neurological disorders",
                "cellular neuroscience ion channels receptors",
                "sensory neuroscience vision hearing touch"
            ]
        }
        
        texts = []
        labels = []
        
        # Generate synthetic examples
        for department, patterns in medical_departments.items():
            for pattern in patterns:
                # Create variations with different researcher names and institutions
                variations = [
                    f"Dr. Smith {pattern}",
                    f"Professor Johnson Harvard University {pattern}",
                    f"Prof. Lee Stanford {pattern}",
                    f"Dr. Chen MIT {pattern}",
                    f"Prof. Garcia University of California {pattern}",
                    f"Dr. Williams Johns Hopkins {pattern}",
                    f"Professor Brown Yale University {pattern}",
                    f"Dr. Davis University of Pennsylvania {pattern}"
                ]
                
                # Add 2-3 variations per pattern
                for i, variation in enumerate(variations[:3]):
                    texts.append(variation)
                    labels.append(department)
        
        # Load existing cache data for high-quality examples
        cache_file = self.base_dir / "pi_department_cache.json"
        if cache_file.exists():
            with open(cache_file, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
            
            cache_examples = 0
            for key, entry in cache_data.items():
                if (entry.get('department', '').lower() != 'unknown' and 
                    entry.get('source') == 'orcid' and 
                    entry.get('confidence') == 'high'):
                    
                    # Parse the key to get name and institution
                    parts = key.split('|')
                    if len(parts) == 2:
                        name, institution = parts
                        dept = entry['department']
                        
                        # Map some departments to our enhanced categories
                        if any(word in dept.lower() for word in ['obstet', 'gynec', 'maternal', 'fetal']):
                            dept = 'Obstetrics and Gynecology'
                        elif any(word in dept.lower() for word in ['pediatr', 'child']):
                            dept = 'Pediatrics'
                        elif any(word in dept.lower() for word in ['cardio', 'heart']):
                            dept = 'Cardiology'
                        elif any(word in dept.lower() for word in ['oncol', 'cancer']):
                            dept = 'Oncology'
                        elif any(word in dept.lower() for word in ['dermat', 'skin']):
                            dept = 'Dermatology'
                        elif any(word in dept.lower() for word in ['psych']):
                            dept = 'Psychiatry'
                        elif any(word in dept.lower() for word in ['orthop', 'bone', 'joint']):
                            dept = 'Orthopedics'
                        elif any(word in dept.lower() for word in ['neurol']):
                            dept = 'Neurology'
                        elif any(word in dept.lower() for word in ['anesth']):
                            dept = 'Anesthesiology'
                        elif any(word in dept.lower() for word in ['radiol', 'imaging']):
                            dept = 'Radiology'
                        elif any(word in dept.lower() for word in ['pathol']):
                            dept = 'Pathology'
                        
                        # Create training example
                        text = f"{name} {institution} {dept}"
                        texts.append(text)
                        labels.append(dept)
                        cache_examples += 1
                        
                        if cache_examples >= 50:  # Limit cache examples
                            break
            
            print(f"Added {cache_examples} examples from cache")
        
        # Create comprehensive training dataset
        training_data = {
            'texts': texts,
            'labels': labels,
            'metadata': {
                'total_examples': len(texts),
                'departments': len(set(labels)),
                'created_with_medical_specialties': True
            }
        }
        
        return training_data
    
    def save_training_data(self, filename: str = "medical_enhanced_training_data.json"):
        """Save the enhanced training data with medical specialties."""
        training_data = self.create_medical_training_data()
        
        output_file = self.base_dir / filename
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(training_data, f, indent=2, ensure_ascii=False)
        
        # Print statistics
        department_counts = {}
        for label in training_data['labels']:
            department_counts[label] = department_counts.get(label, 0) + 1
        
        print(f"Total training examples: {len(training_data['texts'])}")
        print("Department distribution:")
        for dept, count in sorted(department_counts.items()):
            print(f"  {dept}: {count}")
        
        print(f"Saved training data to {filename}")
        return training_data


if __name__ == "__main__":
    builder = MedicalTrainingDataBuilder()
    training_data = builder.save_training_data()
