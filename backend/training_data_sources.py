#!/usr/bin/env python3
"""
Training Data Sources for Department Classification

This module provides various sources to gather training data for academic
department classification beyond ORCID.
"""

import httpx
import json
import asyncio
from typing import List, Dict, Tuple
import re
from pathlib import Path

class TrainingDataCollector:
    """Collect training data from various academic sources."""
    
    def __init__(self):
        self.data = {"texts": [], "labels": []}
    
    async def collect_openalex_data(self, limit: int = 1000) -> List[Tuple[str, str]]:
        """
        Collect training data from OpenAlex API.
        Gets paper titles and their field classifications.
        """
        print("Collecting data from OpenAlex...")
        training_pairs = []
        
        # OpenAlex concept mappings to our departments
        concept_mappings = {
            "Biology": ["biology", "molecular biology", "genetics", "biochemistry", "cell biology"],
            "Chemistry": ["chemistry", "organic chemistry", "physical chemistry", "analytical chemistry"],
            "Physics": ["physics", "quantum mechanics", "astrophysics", "condensed matter physics"],
            "Computer Science": ["computer science", "artificial intelligence", "machine learning", "software engineering"],
            "Engineering": ["engineering", "mechanical engineering", "electrical engineering", "biomedical engineering"],
            "Medicine": ["medicine", "clinical medicine", "pathology", "pharmacology"],
            "Obstetrics and Gynecology": ["obstetrics", "gynecology", "reproductive medicine", "maternal health"],
            "Neuroscience": ["neuroscience", "cognitive neuroscience", "behavioral neuroscience"],
            "Psychology": ["psychology", "cognitive psychology", "social psychology"],
            "Mathematics": ["mathematics", "applied mathematics", "statistics"],
            "Cardiology": ["cardiology", "cardiovascular", "heart disease"],
            "Oncology": ["oncology", "cancer research", "tumor biology"],
            "Immunology": ["immunology", "immune system", "autoimmune"],
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            for dept, keywords in concept_mappings.items():
                for keyword in keywords[:2]:  # Limit to avoid rate limits
                    try:
                        # Search for papers with this keyword
                        url = f"https://api.openalex.org/works"
                        params = {
                            "search": keyword,
                            "filter": "type:journal-article",
                            "per-page": 50,
                            "select": "title,display_name"
                        }
                        
                        response = await client.get(url, params=params)
                        if response.status_code == 200:
                            data = response.json()
                            for work in data.get("results", []):
                                title = work.get("title", "").strip()
                                if title and len(title) > 10:  # Basic quality filter
                                    training_pairs.append((title, dept))
                        
                        # Rate limiting
                        await asyncio.sleep(0.1)
                        
                    except Exception as e:
                        print(f"Error fetching OpenAlex data for {keyword}: {e}")
                        continue
        
        print(f"Collected {len(training_pairs)} examples from OpenAlex")
        return training_pairs
    
    def collect_university_department_data(self) -> List[Tuple[str, str]]:
        """
        Collect training data from university department descriptions.
        This uses synthetic but realistic department descriptions.
        """
        print("Generating university department training data...")
        
        department_descriptions = {
            "Biology": [
                "molecular biology and genetics research laboratory",
                "cell biology and developmental biology studies",
                "ecology and evolutionary biology department",
                "biochemistry and molecular biophysics research",
                "structural biology and protein folding studies",
                "marine biology and aquatic ecosystems research",
                "plant biology and photosynthesis research",
                "microbiology and infectious disease studies"
            ],
            "Chemistry": [
                "organic chemistry synthesis and catalysis",
                "physical chemistry and chemical physics",
                "analytical chemistry and instrumentation",
                "inorganic chemistry and materials science",
                "medicinal chemistry and drug discovery",
                "environmental chemistry and sustainability",
                "computational chemistry and molecular modeling",
                "polymer chemistry and nanotechnology"
            ],
            "Physics": [
                "theoretical physics and quantum mechanics",
                "experimental condensed matter physics",
                "astrophysics and cosmology research",
                "particle physics and high energy studies",
                "optics and photonics laboratory",
                "nuclear physics and radiation studies",
                "biophysics and medical physics",
                "applied physics and engineering physics"
            ],
            "Computer Science": [
                "artificial intelligence and machine learning",
                "computer vision and image processing",
                "software engineering and systems design",
                "cybersecurity and information assurance",
                "data science and computational analytics",
                "human computer interaction research",
                "distributed systems and cloud computing",
                "algorithms and computational complexity"
            ],
            "Engineering": [
                "mechanical engineering and robotics",
                "electrical engineering and signal processing",
                "biomedical engineering and medical devices",
                "chemical engineering and process design",
                "civil engineering and infrastructure",
                "aerospace engineering and flight systems",
                "materials engineering and nanotechnology",
                "environmental engineering and sustainability"
            ],
            "Medicine": [
                "clinical medicine and patient care",
                "medical research and disease treatment",
                "diagnostic medicine and medical imaging",
                "pharmaceutical sciences and drug therapy",
                "public health and epidemiology",
                "medical education and training programs",
                "translational medicine and clinical trials",
                "precision medicine and genomics"
            ],
            "Obstetrics and Gynecology": [
                "maternal fetal medicine and pregnancy care",
                "gynecologic oncology and cancer treatment",
                "reproductive endocrinology and fertility",
                "maternal child health and obstetrics",
                "women's health and preventive care",
                "prenatal diagnosis and genetic counseling",
                "gynecologic surgery and minimally invasive procedures",
                "perinatal medicine and neonatal care"
            ],
            "Neuroscience": [
                "cognitive neuroscience and brain function",
                "behavioral neuroscience and animal models",
                "neurological disorders and brain diseases",
                "synaptic transmission and neural circuits",
                "developmental neuroscience and brain development",
                "computational neuroscience and neural modeling",
                "neuroimaging and brain mapping studies",
                "neuroplasticity and learning mechanisms"
            ],
            "Psychology": [
                "cognitive psychology and mental processes",
                "developmental psychology and child development",
                "social psychology and interpersonal behavior",
                "clinical psychology and mental health",
                "behavioral psychology and learning theory",
                "personality psychology and individual differences",
                "health psychology and behavioral medicine",
                "educational psychology and learning sciences"
            ],
            "Mathematics": [
                "pure mathematics and abstract algebra",
                "applied mathematics and mathematical modeling",
                "statistics and probability theory",
                "computational mathematics and numerical analysis",
                "mathematical physics and theoretical modeling",
                "discrete mathematics and combinatorics",
                "topology and geometric analysis",
                "mathematical biology and biostatistics"
            ],
            "Cardiology": [
                "cardiovascular disease and heart failure",
                "cardiac electrophysiology and arrhythmias",
                "interventional cardiology and catheterization",
                "preventive cardiology and risk assessment",
                "cardiac imaging and echocardiography",
                "heart surgery and cardiac procedures",
                "pediatric cardiology and congenital heart disease",
                "cardiac rehabilitation and exercise physiology"
            ],
            "Oncology": [
                "cancer biology and tumor research",
                "medical oncology and chemotherapy",
                "radiation oncology and cancer treatment",
                "surgical oncology and cancer surgery",
                "cancer immunotherapy and immune responses",
                "pediatric oncology and childhood cancers",
                "cancer prevention and early detection",
                "cancer genetics and hereditary syndromes"
            ],
            "Immunology": [
                "immune system function and autoimmunity",
                "vaccine development and immunization",
                "transplant immunology and organ rejection",
                "allergy and immunologic diseases",
                "cancer immunology and tumor immunity",
                "infectious disease immunology",
                "immunotherapy and biological treatments",
                "innate and adaptive immune responses"
            ]
        }
        
        training_pairs = []
        for dept, descriptions in department_descriptions.items():
            for desc in descriptions:
                training_pairs.append((desc, dept))
        
        print(f"Generated {len(training_pairs)} synthetic department examples")
        return training_pairs
    
    def collect_arxiv_data(self) -> List[Tuple[str, str]]:
        """
        Collect training data based on arXiv category mappings.
        Uses arXiv subject classifications to map to departments.
        """
        print("Generating arXiv-based training data...")
        
        arxiv_mappings = {
            "Physics": [
                "quantum mechanics and field theory research",
                "condensed matter and materials physics",
                "high energy physics and particle interactions",
                "astrophysics and stellar evolution studies",
                "nuclear physics and atomic structure",
                "mathematical physics and theoretical models"
            ],
            "Mathematics": [
                "algebraic geometry and number theory",
                "differential equations and dynamical systems",
                "probability theory and stochastic processes",
                "functional analysis and operator theory",
                "combinatorics and discrete mathematics",
                "topology and geometric structures"
            ],
            "Computer Science": [
                "machine learning and neural networks",
                "algorithms and data structures research",
                "distributed computing and parallel systems",
                "computer graphics and visualization",
                "natural language processing and linguistics",
                "cryptography and security protocols"
            ],
            "Biology": [
                "quantitative biology and bioinformatics",
                "computational biology and genomics",
                "systems biology and network analysis",
                "evolutionary biology and phylogenetics",
                "structural biology and protein analysis",
                "molecular biology and gene expression"
            ]
        }
        
        training_pairs = []
        for dept, examples in arxiv_mappings.items():
            for example in examples:
                training_pairs.append((example, dept))
        
        print(f"Generated {len(training_pairs)} arXiv-based examples")
        return training_pairs
    
    async def collect_all_data(self) -> Dict[str, List[str]]:
        """Collect training data from all sources."""
        all_training_pairs = []
        
        # Collect from various sources
        # all_training_pairs.extend(await self.collect_openalex_data())  # Comment out to avoid API calls
        all_training_pairs.extend(self.collect_university_department_data())
        all_training_pairs.extend(self.collect_arxiv_data())
        
        # Convert to the format expected by SciBERT
        texts = [pair[0] for pair in all_training_pairs]
        labels = [pair[1] for pair in all_training_pairs]
        
        return {"texts": texts, "labels": labels}
    
    def save_training_data(self, data: Dict[str, List[str]], filename: str = "enhanced_training_data.json"):
        """Save training data to JSON file."""
        filepath = Path(__file__).parent / filename
        
        # Load existing data if it exists
        existing_data = {"texts": [], "labels": []}
        if filepath.exists():
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    existing_data = json.load(f)
            except Exception as e:
                print(f"Error loading existing data: {e}")
        
        # Merge with new data
        combined_texts = existing_data["texts"] + data["texts"]
        combined_labels = existing_data["labels"] + data["labels"]
        
        # Remove duplicates while preserving order
        seen = set()
        unique_texts = []
        unique_labels = []
        
        for text, label in zip(combined_texts, combined_labels):
            text_key = text.lower().strip()
            if text_key not in seen:
                seen.add(text_key)
                unique_texts.append(text)
                unique_labels.append(label)
        
        final_data = {"texts": unique_texts, "labels": unique_labels}
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(final_data, f, indent=2, ensure_ascii=False)
        
        print(f"Saved {len(final_data['texts'])} training examples to {filename}")
        return final_data

async def main():
    """Main function to collect and save training data."""
    collector = TrainingDataCollector()
    
    print("Collecting training data from multiple sources...")
    data = await collector.collect_all_data()
    
    print(f"Total collected: {len(data['texts'])} examples")
    
    # Save the data
    collector.save_training_data(data)
    
    # Print some statistics
    from collections import Counter
    label_counts = Counter(data['labels'])
    print("\nTraining data distribution:")
    for label, count in label_counts.most_common():
        print(f"  {label}: {count} examples")

if __name__ == "__main__":
    asyncio.run(main())
