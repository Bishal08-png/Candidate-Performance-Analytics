import os
import sys
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import json
import random
from datetime import datetime

from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, mm
from reportlab.lib import colors
from reportlab.graphics.shapes import Drawing
from reportlab.graphics.renderPDF import drawToFile
from reportlab.graphics.charts.piecharts import Pie
from reportlab.lib.pagesizes import letter
from reportlab.lib.enums import TA_CENTER
from reportlab.graphics.shapes import Image as GraphicsImage

# Define output folder
OUTPUT_FOLDER = 'output'

# Define Font Styles and Colors
HEADER_FONT_SIZE = 14
NORMAL_FONT_SIZE = 10
TITLE_FONT_SIZE = 24
SUBTITLE_FONT_SIZE = 18

H1_COLOR = colors.HexColor('#003366') # Dark Blue
TEXT_COLOR = colors.HexColor('#333333') # Dark Gray
ACCENT_COLOR = colors.HexColor('#6699CC') # Lighter Blue


def generate_assessment_data(num_records: int = 100,
                           num_candidates: int = 20,
                           num_questions: int = 50) -> pd.DataFrame:
    """Generates a synthetic dataset for candidate assessment performance."""
    # Input validation
    if not all(isinstance(arg, int) and arg > 0 for arg in [num_records, num_candidates, num_questions]):
        raise ValueError("All parameters (num_records, num_candidates, num_questions) must be positive integers.")

    if num_records > (num_candidates * num_questions):
        raise ValueError("num_records cannot exceed the total possible unique (candidate, question) pairs.")

    domains = ['NLP', 'LLMs', 'Python', 'Machine Learning', 'Data Science']
    difficulties = ['Easy', 'Medium', 'Hard']
    possible_answers = ['A', 'B', 'C', 'D']

    data = []
    seen_pairs = set() # To prevent duplicate (candidate_id, question_id) pairs

    # Generate records until num_records unique (candidate, question) pairs are achieved
    while len(data) < num_records:
        candidate_id = f'C{random.randint(1, num_candidates):03d}'
        question_id = f'Q{random.randint(1, num_questions):03d}'

        if (candidate_id, question_id) in seen_pairs:
            continue # Skip if this pair has already been generated

        seen_pairs.add((candidate_id, question_id))

        domain = random.choice(domains)
        difficulty = random.choice(difficulties)
        correct_answer = random.choice(possible_answers)

        # Simulate different response scenarios
        r = random.random()
        if r < 0.15:  # 15% chance of unanswered (None or empty string)
            candidate_answer = random.choice([None, '']) # Randomly choose between None and ''
            is_correct = None # Mark as None, cleaning function will handle it as 'Not Attempted'
        elif r < 0.65: # 50% chance of getting it correct if attempted
            candidate_answer = correct_answer
            is_correct = True
        else: # 35% chance of getting it incorrect if attempted
            wrong_answers = [ans for ans in possible_answers if ans != correct_answer]
            candidate_answer = random.choice(wrong_answers) if wrong_answers else 'N/A'
            is_correct = False

        data.append({
            'candidate_id': candidate_id,
            'question_id': question_id,
            'domain': domain,
            'difficulty': difficulty,
            'correct_answer': correct_answer,
            'candidate_answer': candidate_answer,
            'is_correct': is_correct
        })

    df = pd.DataFrame(data)
    return df


def clean_assessment_data(df: pd.DataFrame) -> pd.DataFrame:
    """Cleans the assessment DataFrame by handling missing values and ensuring correct data types."""
    # Create 'is_attempted' column based on candidate_answer being non-null/non-empty
    df['is_attempted'] = df['candidate_answer'].notna() & (df['candidate_answer'] != '')

    # For unattempted questions, 'is_correct' should not be True or False, but rather NaN or None.
    df.loc[~df['is_attempted'], 'is_correct'] = None

    # Fill any remaining None values in 'candidate_answer' with np.nan for consistent representation
    df['candidate_answer'] = df['candidate_answer'].replace('', np.nan).fillna(np.nan)

    # Ensure data types are appropriate
    df['candidate_id'] = df['candidate_id'].astype(str)
    df['question_id'] = df['question_id'].astype(str)
    df['domain'] = df['domain'].astype(str)
    df['difficulty'] = df['difficulty'].astype(str)
    df['correct_answer'] = df['correct_answer'].astype(str)
    df['is_attempted'] = df['is_attempted'].astype(bool)

    print("Data cleaning complete.")
    print("Missing values after cleaning (excluding is_correct for unattempted):")
    print(df.isnull().sum())
    return df


def calculate_overall_metrics(df: pd.DataFrame) -> tuple:
    """Calculates overall accuracy, completion rate, and other overall metrics."""
    total_records_count = len(df)
    attempted_records_count = df['is_attempted'].sum()
    unanswered_records_count = total_records_count - attempted_records_count

    correct_records_count = df[df['is_attempted'] == True]['is_correct'].sum()

    # Calculate Accuracy: (correct answers / total attempted records) * 100
    accuracy = (correct_records_count / attempted_records_count) * 100 if attempted_records_count > 0 else 0

    # Calculate Completion Rate: (attempted records / total records) * 100
    completion_rate = (attempted_records_count / total_records_count) * 100 if total_records_count > 0 else 0

    print(f"\nOverall Accuracy: {accuracy:.2f}%")
    print(f"Overall Completion Rate: {completion_rate:.2f}%")
    print(f"Attempted Records: {attempted_records_count}")
    print(f"Unanswered Records: {unanswered_records_count}")
    print(f"Total Records: {total_records_count}")

    return accuracy, completion_rate, attempted_records_count, unanswered_records_count, total_records_count


def calculate_domain_performance(df: pd.DataFrame) -> dict:
    """Calculates score percentage for each domain, considering only attempted questions."""
    domain_scores = {}
    domains = df['domain'].unique()

    for domain in domains:
        domain_df = df[df['domain'] == domain]
        attempted_in_domain = domain_df[domain_df['is_attempted'] == True]

        if len(attempted_in_domain) > 0:
            correct_in_domain = attempted_in_domain['is_correct'].sum()
            score_percentage = (correct_in_domain / len(attempted_in_domain)) * 100
        else:
            score_percentage = 0
        domain_scores[domain] = round(score_percentage, 2)

    print("\nDomain-wise Performance:")
    for domain, score in domain_scores.items():
        print(f"  {domain}: {score:.2f}%")

    return domain_scores


def calculate_difficulty_performance(df: pd.DataFrame) -> dict:
    """Calculates score percentage for each difficulty level, considering only attempted questions."""
    difficulty_performance = {}
    difficulties = df['difficulty'].unique()

    for difficulty in difficulties:
        difficulty_df = df[df['difficulty'] == difficulty]
        attempted_in_difficulty = difficulty_df[difficulty_df['is_attempted'] == True]

        if len(attempted_in_difficulty) > 0:
            correct_in_difficulty = attempted_in_difficulty['is_correct'].sum()
            score_percentage = (correct_in_difficulty / len(attempted_in_difficulty)) * 100
        else:
            score_percentage = 0
        difficulty_performance[difficulty] = round(score_percentage, 2)

    print("\nDifficulty-wise Performance:")
    for difficulty, score in difficulty_performance.items():
        print(f"  {difficulty}: {score:.2f}%")

    return difficulty_performance


def plot_analytics(analytics_results: dict, output_folder: str = 'output', candidate_id: str = None):
    """Generates visualizations for accuracy, completion rate, domain scores, and difficulty-wise scores and saves them as PNGs."""
    # Set a consistent style for plots
    plt.style.use('seaborn-v0_8-darkgrid')

    # Determine filename prefix
    prefix = f"candidate_{candidate_id}_" if candidate_id else "overall_"

    # 1. Overall Accuracy and Completion Rate (Bar Chart)
    plt.figure(figsize=(8, 6))
    metrics_labels = ['Accuracy', 'Completion Rate']
    metrics_values = [analytics_results['accuracy'], analytics_results['completion_rate']]
    plt.bar(metrics_labels, metrics_values, color=['skyblue', 'lightcoral'])
    plt.ylim(0, 100)
    plt.ylabel('Percentage (%)')
    plt.title(f'{prefix.replace("_", " ").title()}Performance Metrics')
    for i, v in enumerate(metrics_values):
        plt.text(i, v + 2, f"{v:.2f}%", ha='center', va='bottom')
    plt.tight_layout()
    plt.savefig(os.path.join(output_folder, f'{prefix}overall_performance.png'))
    plt.close()

    # 2. Domain-wise Performance (Bar Chart)
    plt.figure(figsize=(10, 6))
    domain_names = list(analytics_results['domain_scores'].keys())
    domain_scores = list(analytics_results['domain_scores'].values())
    plt.bar(domain_names, domain_scores, color='lightgreen')
    plt.ylim(0, 100)
    plt.ylabel('Score Percentage (%)')
    plt.title(f'{prefix.replace("_", " ").title()}Domain-wise Performance')
    plt.xticks(rotation=45, ha='right')
    for i, v in enumerate(domain_scores):
        plt.text(i, v + 2, f"{v:.2f}%", ha='center', va='bottom')
    plt.tight_layout()
    plt.savefig(os.path.join(output_folder, f'{prefix}domain_performance.png'))
    plt.close()

    # 3. Difficulty-wise Performance (Bar Chart)
    plt.figure(figsize=(8, 6))
    difficulty_levels = list(analytics_results['difficulty_performance'].keys())
    difficulty_scores = list(analytics_results['difficulty_performance'].values())
    plt.bar(difficulty_levels, difficulty_scores, color='gold')
    plt.ylim(0, 100)
    plt.ylabel('Score Percentage (%)')
    plt.title(f'{prefix.replace("_", " ").title()}Difficulty-wise Performance')
    for i, v in enumerate(difficulty_scores):
        plt.text(i, v + 2, f"{v:.2f}%", ha='center', va='bottom')
    plt.tight_layout()
    plt.savefig(os.path.join(output_folder, f'{prefix}difficulty_performance.png'))
    plt.close()


def convert_numpy(obj):
    """Convert NumPy types to native Python types for JSON serialization."""
    if isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.bool_):
        return bool(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    raise TypeError(f"Object of type {obj.__class__.__name__} is not JSON serializable")


def export_results(analytics_data: dict, df: pd.DataFrame, json_filename: str = 'candidate_analytics.json', csv_filename: str = 'analytics_dataset.csv'):
    """Exports analytics results to JSON and the cleaned dataset to CSV."""
    with open(json_filename, 'w') as f:
        json.dump(analytics_data, f, indent=4, default=convert_numpy)
    print(f"Analytics results exported to {json_filename}")

    df.to_csv(csv_filename, index=False)
    print(f"Cleaned dataset exported to {csv_filename}")


def generate_performance_grade(accuracy: float) -> dict:
    """Generates a performance grade, classification, and pass/fail status based on accuracy."""
    if accuracy >= 90:
        grade = 'A'
        classification = 'Excellent'
        pass_fail = 'Pass'
    elif accuracy >= 80:
        grade = 'B'
        classification = 'Very Good'
        pass_fail = 'Pass'
    elif accuracy >= 70:
        grade = 'C'
        classification = 'Good'
        pass_fail = 'Pass'
    elif accuracy >= 60:
        grade = 'D'
        classification = 'Average'
        pass_fail = 'Pass'
    else:
        grade = 'F'
        classification = 'Needs Improvement'
        pass_fail = 'Fail'

    return {
        'grade': grade,
        'classification': classification,
        'pass_fail': pass_fail
    }


def generate_insights(analytics_results: dict) -> dict:
    """Analyzes domain and difficulty scores to identify strengths and areas for improvement."""
    overall_accuracy = analytics_results.get('accuracy', 0.0)
    completion_rate = analytics_results.get('completion_rate', 0.0)
    domain_scores = analytics_results.get('domain_scores', {})
    difficulty_performance = analytics_results.get('difficulty_performance', {})

    insights = {
        'overall_accuracy': overall_accuracy,
        'completion_rate': completion_rate,
        'strengths': {
            'domains': [],
            'difficulty': None
        },
        'areas_for_improvement': {
            'domains': [],
            'difficulty': None
        },
        'overall_interpretation': ''
    }

    # Identify strongest and weakest domains
    if domain_scores:
        sorted_domains = sorted(domain_scores.items(), key=lambda item: item[1], reverse=True)
        insights['strengths']['domains'] = [dom for dom, score in sorted_domains[:min(3, len(sorted_domains))]]
        insights['areas_for_improvement']['domains'] = [dom for dom, score in sorted_domains[len(sorted_domains)-min(3, len(sorted_domains)):] if score <= 60]

    # Identify strongest and weakest difficulty levels
    if difficulty_performance:
        sorted_difficulty = sorted(difficulty_performance.items(), key=lambda item: item[1], reverse=True)
        insights['strengths']['difficulty'] = sorted_difficulty[0][0] if sorted_difficulty else None
        insights['areas_for_improvement']['difficulty'] = sorted_difficulty[-1][0] if sorted_difficulty else None

    # Construct overall interpretation
    interpretation_parts = []
    interpretation_parts.append(f"The candidate achieved an overall accuracy of {overall_accuracy:.2f}% and a completion rate of {completion_rate:.2f}%.")

    if insights['strengths']['domains']:
        interpretation_parts.append(f"\nStrengths were observed in domains such as: {', '.join(insights['strengths']['domains'])}.")
    if insights['areas_for_improvement']['domains']:
        interpretation_parts.append(f"Areas for improvement include domains like: {', '.join(insights['areas_for_improvement']['domains'])}.")
    elif len(domain_scores) > 0 and not insights['areas_for_improvement']['domains']:
        interpretation_parts.append(f"No significant weaknesses identified in any specific domain.")

    if insights['strengths']['difficulty']:
        interpretation_parts.append(f"The candidate performed strongest in {insights['strengths']['difficulty']} level questions.")
    if insights['areas_for_improvement']['difficulty']:
        interpretation_parts.append(f"Performance was weakest in {insights['areas_for_improvement']['difficulty']} level questions.")

    insights['overall_interpretation'] = " ".join(interpretation_parts).strip()

    return insights


def _create_cover_page(canvas, doc, analytics_results, candidate_id, current_datetime):
    """Generates the cover page for the PDF report."""
    canvas.saveState()
    canvas.setFont('Helvetica-Bold', TITLE_FONT_SIZE)
    canvas.setFillColor(H1_COLOR)
    canvas.drawCentredString(letter[0]/2.0, letter[1]-inch*2, "Candidate Performance Assessment Report")

    if candidate_id:
        canvas.setFont('Helvetica', SUBTITLE_FONT_SIZE)
        canvas.setFillColor(TEXT_COLOR)
        canvas.drawCentredString(letter[0]/2.0, letter[1]-inch*2.5, f"Candidate ID: {candidate_id}")

    canvas.setFont('Helvetica', NORMAL_FONT_SIZE)
    canvas.setFillColor(TEXT_COLOR)
    canvas.drawCentredString(letter[0]/2.0, inch, f"Report Generated: {current_datetime}")

    canvas.restoreState()


def _create_executive_summary(analytics_results, insight_data, grade_data, styles):
    """Generates the executive summary page content."""
    story = []

    story.append(Paragraph("Executive Summary", styles['h1']))
    story.append(Spacer(1, 0.2 * inch))

    # Overall Performance
    story.append(Paragraph("Overall Performance", styles['h2']))
    story.append(Paragraph(f"<b>Grade:</b> <font color='{ACCENT_COLOR.hexval()}'>{grade_data['grade']} ({grade_data['classification']}) - {grade_data['pass_fail']}</font>", styles['Normal']))
    story.append(Paragraph(f"<b>Overall Accuracy:</b> {analytics_results['accuracy']:.2f}%", styles['Normal']))
    story.append(Paragraph(f"<b>Completion Rate:</b> {analytics_results['completion_rate']:.2f}%", styles['Normal']))
    story.append(Spacer(1, 0.2 * inch))

    # AI-Based Insights Summary
    story.append(Paragraph("AI-Based Insights", styles['h2']))
    story.append(Paragraph(insight_data['overall_interpretation'], styles['Normal']))
    story.append(Spacer(1, 0.2 * inch))

    story.append(PageBreak())
    return story


def _create_performance_dashboard(candidate_id, styles, output_folder):
    """Generates the performance dashboard page content with embedded charts."""
    story = []

    story.append(Paragraph("Performance Dashboard", styles['h1']))
    story.append(Spacer(1, 0.2 * inch))

    prefix = f"candidate_{candidate_id}_" if candidate_id else "overall_"

    # Helper to add image to story using Drawing
    def add_chart_to_story(chart_path, title_text):
        if os.path.exists(chart_path):
            story.append(Paragraph(title_text, styles['h2']))
            # Create a Drawing object to hold the image
            drawing_width = 5.5 * inch
            drawing_height = 4.5 * inch
            drawing = Drawing(drawing_width, drawing_height)
            drawing.add(GraphicsImage(0, 0, drawing_width, drawing_height, chart_path))
            story.append(drawing)
            story.append(Spacer(1, 0.1 * inch))
        else:
            story.append(Paragraph(f"{title_text} chart not found at {chart_path}", styles['Normal']))

    # Embed Overall Performance Chart
    add_chart_to_story(os.path.join(output_folder, f'{prefix}overall_performance.png'), "Overall Performance Metrics")

    # Embed Domain-wise Performance Chart
    add_chart_to_story(os.path.join(output_folder, f'{prefix}domain_performance.png'), "Domain-wise Performance")

    # Embed Difficulty-wise Performance Chart
    add_chart_to_story(os.path.join(output_folder, f'{prefix}difficulty_performance.png'), "Difficulty-wise Performance")

    story.append(PageBreak())
    return story


def _create_domain_analysis(analytics_results, insight_data, styles):
    """Generates the domain-wise analysis page content."""
    story = []

    story.append(Paragraph("Domain-wise Performance Analysis", styles['h1']))
    story.append(Spacer(1, 0.2 * inch))

    story.append(Paragraph("Individual Domain Scores:", styles['h2']))
    domain_scores = analytics_results.get('domain_scores', {})
    if domain_scores:
        for domain, score in domain_scores.items():
            story.append(Paragraph(f"<b>{domain}:</b> {score:.2f}% Accuracy", styles['Normal']))
    else:
        story.append(Paragraph("No domain performance data available.", styles['Normal']))

    story.append(Spacer(1, 0.2 * inch))
    story.append(Paragraph("Strengths and Areas for Improvement:", styles['h2']))

    strengths_domains = insight_data['strengths']['domains']
    if strengths_domains:
        story.append(Paragraph(f"<b>Strongest Domains:</b> {', '.join(strengths_domains)}", styles['Normal']))
    else:
        story.append(Paragraph("No specific strong domains identified.", styles['Normal']))

    areas_for_improvement_domains = insight_data['areas_for_improvement']['domains']
    if areas_for_improvement_domains:
        story.append(Paragraph(f"<b>Domains for Improvement:</b> <font color='red'>{', '.join(areas_for_improvement_domains)}</font>", styles['Normal']))
    else:
        story.append(Paragraph("No specific domains for improvement identified below 60% accuracy.", styles['Normal']))

    story.append(PageBreak())
    return story


def _create_difficulty_analysis(analytics_results, insight_data, styles):
    """Generates the difficulty-wise analysis page content."""
    story = []

    story.append(Paragraph("Difficulty-wise Performance Analysis", styles['h1']))
    story.append(Spacer(1, 0.2 * inch))

    story.append(Paragraph("Individual Difficulty Scores:", styles['h2']))
    difficulty_performance = analytics_results.get('difficulty_performance', {})
    if difficulty_performance:
        for difficulty, score in difficulty_performance.items():
            story.append(Paragraph(f"<b>{difficulty}:</b> {score:.2f}% Accuracy", styles['Normal']))
    else:
        story.append(Paragraph("No difficulty performance data available.", styles['Normal']))

    story.append(Spacer(1, 0.2 * inch))
    story.append(Paragraph("Strengths and Areas for Improvement:", styles['h2']))

    strongest_difficulty = insight_data['strengths']['difficulty']
    if strongest_difficulty:
        story.append(Paragraph(f"<b>Strongest Difficulty Level:</b> {strongest_difficulty}", styles['Normal']))
    else:
        story.append(Paragraph("No specific strong difficulty level identified.", styles['Normal']))

    areas_for_improvement_difficulty = insight_data['areas_for_improvement']['difficulty']
    if areas_for_improvement_difficulty:
        story.append(Paragraph(f"<b>Difficulty Level for Improvement:</b> <font color='red'>{areas_for_improvement_difficulty}</font>", styles['Normal']))
    else:
        story.append(Paragraph("No specific difficulty level for improvement identified.", styles['Normal']))

    story.append(PageBreak())
    return story


def _create_ai_insights(insight_data, styles):
    """Generates the AI-based insights page content."""
    story = []

    story.append(Paragraph("AI-Based Insights and Recommendations", styles['h1']))
    story.append(Spacer(1, 0.2 * inch))

    story.append(Paragraph("Overall Interpretation:", styles['h2']))
    story.append(Paragraph(insight_data['overall_interpretation'], styles['Normal']))
    story.append(Spacer(1, 0.2 * inch))

    story.append(Paragraph("Identified Strengths:", styles['h2']))
    if insight_data['strengths']['domains']:
        story.append(Paragraph(f"<b>Strongest Domains:</b> {', '.join(insight_data['strengths']['domains'])}", styles['Normal']))
    else:
        story.append(Paragraph("No specific strong domains identified.", styles['Normal']))

    if insight_data['strengths']['difficulty']:
        story.append(Paragraph(f"<b>Strongest Difficulty Level:</b> {insight_data['strengths']['difficulty']}", styles['Normal']))
    else:
        story.append(Paragraph("No specific strong difficulty level identified.", styles['Normal']))
    story.append(Spacer(1, 0.2 * inch))

    story.append(Paragraph("Areas for Improvement:", styles['h2']))
    if insight_data['areas_for_improvement']['domains']:
        story.append(Paragraph(f"<b>Domains for Improvement:</b> <font color='red'>{', '.join(insight_data['areas_for_improvement']['domains'])}</font>", styles['Normal']))
    else:
        story.append(Paragraph("No specific domains for improvement identified below 60% accuracy.", styles['Normal']))

    if insight_data['areas_for_improvement']['difficulty']:
        story.append(Paragraph(f"<b>Difficulty Level for Improvement:</b> <font color='red'>{insight_data['areas_for_improvement']['difficulty']}</font>", styles['Normal']))
    else:
        story.append(Paragraph("No specific difficulty level for improvement identified.", styles['Normal']))

    story.append(PageBreak())
    return story


def _create_final_evaluation(insight_data, grade_data, styles):
    """Generates the final evaluation page content."""
    story = []

    story.append(Paragraph("Final Evaluation and Recommendations", styles['h1']))
    story.append(Spacer(1, 0.2 * inch))

    story.append(Paragraph(f"Based on the assessment, the candidate's overall performance is rated as <b>{grade_data['classification']}</b> with a grade of <b>{grade_data['grade']}</b>. The candidate's performance resulted in a <b>{grade_data['pass_fail']}</b> status.", styles['Normal']))
    story.append(Spacer(1, 0.2 * inch))

    story.append(Paragraph("Summary of Strengths:", styles['h2']))
    if insight_data['strengths']['domains']:
        story.append(Paragraph(f"- Strong performance in domains: {', '.join(insight_data['strengths']['domains'])}", styles['Normal']))
    if insight_data['strengths']['difficulty']:
        story.append(Paragraph(f"- Demonstrated proficiency in {insight_data['strengths']['difficulty']} level questions.", styles['Normal']))
    if not insight_data['strengths']['domains'] and not insight_data['strengths']['difficulty']:
        story.append(Paragraph("- No specific strengths identified beyond overall good performance.", styles['Normal']))
    story.append(Spacer(1, 0.1 * inch))

    story.append(Paragraph("Recommendations for Improvement:", styles['h2']))
    if insight_data['areas_for_improvement']['domains']:
        story.append(Paragraph(f"- Focus on improving knowledge and skills in domains such as: <font color='red'>{', '.join(insight_data['areas_for_improvement']['domains'])}</font>.", styles['Normal']))
    if insight_data['areas_for_improvement']['difficulty']:
        story.append(Paragraph(f"- Practice more {insight_data['areas_for_improvement']['difficulty']} level questions to enhance problem-solving in challenging scenarios.", styles['Normal']))
    if not insight_data['areas_for_improvement']['domains'] and not insight_data['areas_for_improvement']['difficulty']:
        story.append(Paragraph("- Continue to reinforce existing knowledge to maintain a high level of performance.", styles['Normal']))
    story.append(Spacer(1, 0.2 * inch))

    story.append(Paragraph("Next Steps:", styles['h2']))
    story.append(Paragraph("- Review the detailed performance dashboard for a granular view of strengths and weaknesses.", styles['Normal']))
    story.append(Paragraph("- Consider targeted learning resources or practice sessions for identified areas of improvement.", styles['Normal']))

    return story


def _page_number_canvas(canvas, doc):
    """Adds page numbers to each page of the PDF."""
    canvas.saveState()
    canvas.setFont('Helvetica', 9)
    page_number_text = f"Page {doc.page}"
    canvas.drawRightString(letter[0] - inch, 0.75 * inch, page_number_text)
    canvas.restoreState()


def generate_pdf_report(analytics_results: dict,
                        candidate_id: str = None,
                        current_datetime: str = None,
                        output_folder: str = OUTPUT_FOLDER,
                        insight_data: dict = None,
                        grade_data: dict = None):
    """Generates a multi-page PDF performance report."""
    if current_datetime is None:
        current_datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Determine filename
    filename_prefix = f"candidate_report_{candidate_id}" if candidate_id else "overall_report"
    pdf_filename = os.path.join(output_folder, f"{filename_prefix}.pdf")

    doc = SimpleDocTemplate(pdf_filename, pagesize=letter)
    story = []

    # Add a PageBreak to force the story content to start on a new page after the cover page
    story.append(PageBreak())

    # Get standard styles and customize
    styles = getSampleStyleSheet()

    styles['h1'].fontSize = TITLE_FONT_SIZE
    styles['h1'].leading = TITLE_FONT_SIZE * 1.2
    styles['h1'].alignment = TA_CENTER
    styles['h1'].fontName = 'Helvetica-Bold'
    styles['h1'].textColor = H1_COLOR

    styles['h2'].fontSize = HEADER_FONT_SIZE
    styles['h2'].leading = HEADER_FONT_SIZE * 1.2
    styles['h2'].fontName = 'Helvetica-Bold'
    styles['h2'].textColor = H1_COLOR

    styles['Normal'].fontSize = NORMAL_FONT_SIZE
    styles['Normal'].leading = NORMAL_FONT_SIZE * 1.2
    styles['Normal'].fontName = 'Helvetica'
    styles['Normal'].textColor = TEXT_COLOR

    # Executive Summary
    story.extend(_create_executive_summary(analytics_results, insight_data, grade_data, styles))

    # Performance Dashboard
    story.extend(_create_performance_dashboard(candidate_id, styles, output_folder))

    # Domain Analysis
    story.extend(_create_domain_analysis(analytics_results, insight_data, styles))

    # Difficulty Analysis
    story.extend(_create_difficulty_analysis(analytics_results, insight_data, styles))

    # AI-Based Insights
    story.extend(_create_ai_insights(insight_data, styles))

    # Final Evaluation
    story.extend(_create_final_evaluation(insight_data, grade_data, styles))

    # Build the PDF document
    try:
        doc.build(story, onFirstPage=lambda canvas, doc: _create_cover_page(canvas, doc, analytics_results, candidate_id, current_datetime), onLaterPages=_page_number_canvas)
        print(f"PDF report generated successfully: {pdf_filename}")
    except Exception as e:
        print(f"Error generating PDF report: {e}")


def generate_text_report(
    candidate_analytics: dict,
    candidate_id: str = None,
    current_datetime: str = None,
    output_folder: str = 'output',
    insight_data: dict = None,
    grade_data: dict = None
):
    """Generates a professional console report and saves it to a text file."""
    if current_datetime is None:
        current_datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    filename_prefix = f"candidate_report_{candidate_id}" if candidate_id else "overall_report"
    text_filename = os.path.join(output_folder, f"{filename_prefix}.txt")

    report_content = []
    report_content.append(f"Candidate Performance Assessment Report")
    report_content.append(f"Generated On: {current_datetime}")
    if candidate_id:
        report_content.append(f"Candidate ID: {candidate_id}")
    report_content.append("=" * 60)
    report_content.append("\n")

    # Executive Summary / Overall Performance
    report_content.append("### Executive Summary\n")
    report_content.append(f"Overall Accuracy: {candidate_analytics['accuracy']:.2f}%")
    report_content.append(f"Completion Rate: {candidate_analytics['completion_rate']:.2f}%")
    report_content.append(f"Grade: {grade_data['grade']} ({grade_data['classification']}) - {grade_data['pass_fail']}")
    report_content.append("\n")

    # Domain-wise Performance
    report_content.append("### Domain-wise Performance\n")
    domain_scores = candidate_analytics.get('domain_scores', {})
    if domain_scores:
        for domain, score in domain_scores.items():
            report_content.append(f"- {domain}: {score:.2f}%")
    else:
        report_content.append("No domain performance data available.")
    report_content.append("\n")

    # Difficulty-wise Performance
    report_content.append("### Difficulty-wise Performance\n")
    difficulty_performance = candidate_analytics.get('difficulty_performance', {})
    if difficulty_performance:
        for difficulty, score in difficulty_performance.items():
            report_content.append(f"- {difficulty}: {score:.2f}%")
    else:
        report_content.append("No difficulty performance data available.")
    report_content.append("\n")

    # AI-Based Insights
    report_content.append("### AI-Based Insights\n")
    if insight_data:
        report_content.append(f"Overall Interpretation: {insight_data['overall_interpretation']}")
        if insight_data['strengths']['domains']:
            report_content.append(f"Strongest Domains: {', '.join(insight_data['strengths']['domains'])}")
        if insight_data['strengths']['difficulty']:
            report_content.append(f"Strongest Difficulty Level: {insight_data['strengths']['difficulty']}")
        if insight_data['areas_for_improvement']['domains']:
            report_content.append(f"Areas for Improvement (Domains): {', '.join(insight_data['areas_for_improvement']['domains'])}")
        if insight_data['areas_for_improvement']['difficulty']:
            report_content.append(f"Areas for Improvement (Difficulty): {insight_data['areas_for_improvement']['difficulty']}")
    else:
        report_content.append("No AI insights available.")
    report_content.append("\n")

    # Final Evaluation
    report_content.append("### Final Evaluation and Recommendations\n")
    if grade_data and insight_data:
        report_content.append(f"Based on the assessment, the candidate's overall performance is rated as {grade_data['classification']} with a grade of {grade_data['grade']}. The candidate's performance resulted in a {grade_data['pass_fail']} status.")
        report_content.append("\n")

        report_content.append("Summary of Strengths:")
        if insight_data['strengths']['domains']:
            report_content.append(f"- Strong performance in domains: {', '.join(insight_data['strengths']['domains'])}")
        if insight_data['strengths']['difficulty']:
            report_content.append(f"- Demonstrated proficiency in {insight_data['strengths']['difficulty']} level questions.")
        if not insight_data['strengths']['domains'] and not insight_data['strengths']['difficulty']:
            report_content.append("- No specific strengths identified beyond overall good performance.")
        report_content.append("\n")

        report_content.append("Recommendations for Improvement:")
        if insight_data['areas_for_improvement']['domains']:
            report_content.append(f"- Focus on improving knowledge and skills in domains such as: {', '.join(insight_data['areas_for_improvement']['domains'])}.")
        if insight_data['areas_for_improvement']['difficulty']:
            report_content.append(f"- Practice more {insight_data['areas_for_improvement']['difficulty']} level questions to enhance problem-solving in challenging scenarios.")
        if not insight_data['areas_for_improvement']['domains'] and not insight_data['areas_for_improvement']['difficulty']:
            report_content.append("- Continue to reinforce existing knowledge to maintain a high level of performance.")
        report_content.append("\n")

        report_content.append("Next Steps:")
        report_content.append("- Review the detailed performance dashboard for a granular view of strengths and weaknesses.")
        report_content.append("- Consider targeted learning resources or practice sessions for identified areas of improvement.")
    else:
        report_content.append("No final evaluation data available.")
    report_content.append("\n")

    report_content_str = "\n".join(report_content)

    with open(text_filename, 'w') as f:
        f.write(report_content_str)

    print(f"Text report generated successfully: {text_filename}")
    print("\n--- Text Report Content ---\n")
    print(report_content_str)


def get_positive_integer_input(prompt_message: str, default_value: int) -> int:
    """Helper function to get and validate a positive integer from user input."""
    if not sys.stdin.isatty():
        print(f"{prompt_message} (default: {default_value}): [Non-interactive, using default]")
        return default_value
    while True:
        try:
            user_input = input(f"{prompt_message} (default: {default_value}): ")
            if not user_input:
                return default_value
            value = int(user_input)
            if value <= 0:
                print("Input must be a positive integer. Please try again.")
            else:
                return value
        except ValueError:
            print("Invalid input. Please enter a positive integer.")


def get_candidate_id_input(available_ids: list) -> str:
    """Helper function to get and validate a candidate ID from user input."""
    if not sys.stdin.isatty():
        default_id = sorted(available_ids)[0] if available_ids else ""
        print(f"Available Candidate IDs: {', '.join(sorted(available_ids))}")
        print(f"Enter a Candidate ID for analysis: [Non-interactive, selected: {default_id}]")
        return default_id
    while True:
        print("\n--- Candidate Selection ---")
        print("Available Candidate IDs:")
        print(', '.join(sorted(available_ids)))
        candidate_input = input("Enter a Candidate ID for analysis: ").strip()

        if not candidate_input:
            print("Input cannot be empty. Please enter a valid Candidate ID.")
        elif candidate_input not in available_ids:
            print(f"Candidate ID '{candidate_input}' not found. Please choose from the available IDs.")
        else:
            return candidate_input


def main():
    if not os.path.exists(OUTPUT_FOLDER):
        os.makedirs(OUTPUT_FOLDER)
    print("\n--- Dataset Generation Parameters ---")
    num_candidates_input = get_positive_integer_input("Enter the number of candidates", 20)
    num_questions_input = get_positive_integer_input("Enter the number of questions", 50)
    num_records_input = get_positive_integer_input("Enter the number of assessment records to generate", 150)

    try:
        assessment_df = generate_assessment_data(
            num_records=num_records_input,
            num_candidates=num_candidates_input,
            num_questions=num_questions_input
        )
        print(f"\nGenerated Assessment Dataset with {len(assessment_df)} records.")
        print(f"Unique Candidates: {assessment_df['candidate_id'].nunique()}")
        print(f"Unique Questions: {assessment_df['question_id'].nunique()}")
    except ValueError as e:
        print(f"Error generating dataset: {e}")
        assessment_df = pd.DataFrame()

    if assessment_df.empty:
        print("Dataset generation failed. Exiting.")
        return

    # Clean the raw dataset
    cleaned_df = clean_assessment_data(assessment_df.copy())

    # Calculate overall metrics
    overall_accuracy, overall_completion_rate, attempted_q, unanswered_q, total_records = calculate_overall_metrics(cleaned_df)
    
    analytics_results = {
        "accuracy": round(overall_accuracy, 2),
        "completion_rate": round(overall_completion_rate, 2),
        "attempted_questions": int(attempted_q),
        "unanswered_questions": int(unanswered_q),
        "total_questions": total_records
    }

    # Calculate overall domain and difficulty performance
    overall_domain_scores = calculate_domain_performance(cleaned_df)
    analytics_results["domain_scores"] = overall_domain_scores

    overall_difficulty_scores = calculate_difficulty_performance(cleaned_df)
    analytics_results["difficulty_performance"] = overall_difficulty_scores

    # Generate overall plots
    print("Generating overall visualizations...")
    plot_analytics(analytics_results, output_folder=OUTPUT_FOLDER)
    print("Overall visualizations generated successfully!")

    # Export overall results
    export_results(
        analytics_results, 
        cleaned_df, 
        json_filename=os.path.join(OUTPUT_FOLDER, 'candidate_analytics.json'), 
        csv_filename=os.path.join(OUTPUT_FOLDER, 'analytics_dataset.csv')
    )

    # Generate overall reports
    current_datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    overall_grade_data = generate_performance_grade(analytics_results['accuracy'])
    overall_insight_data = generate_insights(analytics_results)

    generate_text_report(
        candidate_analytics=analytics_results,
        current_datetime=current_datetime,
        output_folder=OUTPUT_FOLDER,
        insight_data=overall_insight_data,
        grade_data=overall_grade_data
    )

    generate_pdf_report(
        analytics_results=analytics_results,
        current_datetime=current_datetime,
        output_folder=OUTPUT_FOLDER,
        insight_data=overall_insight_data,
        grade_data=overall_grade_data
    )

    # Candidate Selection
    unique_candidate_ids = cleaned_df['candidate_id'].unique().tolist()
    selected_candidate_id = get_candidate_id_input(unique_candidate_ids)
    print(f"\nSelected Candidate for Analysis: {selected_candidate_id}")

    candidate_df = cleaned_df[cleaned_df['candidate_id'] == selected_candidate_id].copy()
    print(f"Filtered data for Candidate {selected_candidate_id}: {len(candidate_df)} records.")

    if not candidate_df.empty:
        print(f"\n--- Analytics for Candidate: {selected_candidate_id} ---")
        overall_accuracy_candidate, overall_completion_rate_candidate, attempted_q_candidate, unanswered_q_candidate, total_records_candidate = calculate_overall_metrics(candidate_df)

        analytics_results_candidate = {
            "candidate_id": selected_candidate_id,
            "accuracy": round(overall_accuracy_candidate, 2),
            "completion_rate": round(overall_completion_rate_candidate, 2),
            "attempted_questions": int(attempted_q_candidate),
            "unanswered_questions": int(unanswered_q_candidate),
            "total_questions": total_records_candidate
        }

        domain_scores_candidate = calculate_domain_performance(candidate_df)
        analytics_results_candidate["domain_scores"] = domain_scores_candidate

        difficulty_performance_candidate = calculate_difficulty_performance(candidate_df)
        analytics_results_candidate["difficulty_performance"] = difficulty_performance_candidate

        print("\nFinal Analytics Results for Selected Candidate:")
        print(json.dumps(analytics_results_candidate, indent=2, default=convert_numpy))

        # Generate candidate plots
        print(f"Generating visualizations for Candidate: {selected_candidate_id}...")
        plot_analytics(analytics_results_candidate, output_folder=OUTPUT_FOLDER, candidate_id=selected_candidate_id)
        print("Visualizations generated successfully for selected candidate!")

        # Export candidate results
        candidate_json_filename = os.path.join(OUTPUT_FOLDER, f'candidate_analytics_{selected_candidate_id}.json')
        candidate_csv_filename = os.path.join(OUTPUT_FOLDER, f'analytics_dataset_{selected_candidate_id}.csv')
        export_results(
            analytics_results_candidate, 
            candidate_df, 
            json_filename=candidate_json_filename, 
            csv_filename=candidate_csv_filename
        )

        # Generate candidate reports
        candidate_grade_data = generate_performance_grade(analytics_results_candidate['accuracy'])
        candidate_insight_data = generate_insights(analytics_results_candidate)

        generate_text_report(
            candidate_analytics=analytics_results_candidate,
            candidate_id=selected_candidate_id,
            current_datetime=current_datetime,
            output_folder=OUTPUT_FOLDER,
            insight_data=candidate_insight_data,
            grade_data=candidate_grade_data
        )

        generate_pdf_report(
            analytics_results=analytics_results_candidate,
            candidate_id=selected_candidate_id,
            current_datetime=current_datetime,
            output_folder=OUTPUT_FOLDER,
            insight_data=candidate_insight_data,
            grade_data=candidate_grade_data
        )

        print(f"\nReporting integrated and reports generated for Candidate: {selected_candidate_id}.")
    else:
        print("No data available for candidate selection.")


if __name__ == '__main__':
    main()
