from pyramid.response import Response
from pyramid.renderers import render
from weasyprint import HTML, CSS
from sqlalchemy.orm import joinedload
import random
import math
import json
from markupsafe import Markup
import io
from base64 import b64encode, b64decode
from PIL import Image, ImageDraw, ImageFont
import os

from riskmatrix.i18n import _
from riskmatrix.models import Organization, RiskAssessment, RiskAssessmentInfo
from riskmatrix.models.risk_assessment_info import RiskAssessmentState
from riskmatrix.views.risk_assessment import render_risk_matrix

from typing import TYPE_CHECKING, List, Dict, Tuple, Any, Optional, Union
if TYPE_CHECKING:
    from pyramid.interfaces import IRequest


class ReportView:
    def __init__(self, risks_data):
        self.risks_data = risks_data
        self.grid_size = 5
        self.cell_size = 16  # Cell size in mm for PDF
        self.dot_size = 6    # Dot size in mm for PDF
        self.padding = 2     # Padding in mm for PDF
        
    def get_cell_color(self, impact: int, likelihood: int) -> str:
        """Determine cell background class based on impact and likelihood."""
        # High risk (red) cells
        if ((impact >= 4 and likelihood >= 4) or
            (impact == 5 and likelihood >= 3) or
            (impact >= 3 and likelihood == 5)):
            return 'cell-red'
        # Low risk (green) cells
        elif ((impact <= 2 and likelihood <= 2) or
              (impact == 1 and likelihood <= 3) or
              (likelihood == 1 and impact <= 3)):
            return 'cell-green'
        # Medium risk (yellow) cells
        else:
            return 'cell-yellow'
            
    def get_cell_color_rgb(self, impact: int, likelihood: int) -> Tuple[int, int, int]:
        """Get the RGB color for a cell based on its risk level."""
        cell_class = self.get_cell_color(impact, likelihood)
        if cell_class == 'cell-red':
            return (254, 202, 202)  # #fecaca - light red
        elif cell_class == 'cell-yellow':
            return (253, 230, 138)  # #fde68a - light yellow
        elif cell_class == 'cell-green':
            return (187, 247, 208)  # #bbf7d0 - light green
        return (255, 255, 255)  # white as fallback
        
    def generate_random_positions(self, total: int, cell_width: int, cell_height: int) -> List[Dict[str, int]]:
        """Generate non-overlapping random positions for risk dots within a cell."""
        if total == 0:
            return []

        # Calculate dot size and padding relative to cell dimensions
        # Assuming square cells for simplicity in ratio calculation
        dot_size_ratio = 0.18  # Consistent with PNG/SVG rendering
        padding_ratio = 0.05   # Use 5% padding
        effective_dot_size = cell_width * dot_size_ratio
        effective_padding = cell_width * padding_ratio
            
        positions = []
        max_attempts = 50
        
        for _ in range(total):
            new_pos = None
            attempts = 0
            
            while attempts < max_attempts:
                # Generate a random position within the cell boundaries using relative sizes
                available_width = cell_width - effective_dot_size - 2 * effective_padding
                available_height = cell_height - effective_dot_size - 2 * effective_padding
                
                # Ensure available space is not negative if padding/dot size is large
                available_width = max(0, available_width)
                available_height = max(0, available_height)
                
                left = effective_padding + random.random() * available_width
                top = effective_padding + random.random() * available_height
                
                # Check if this position overlaps with existing dots
                overlaps = False
                for pos in positions:
                    distance = math.hypot(pos['left'] - left, pos['top'] - top)
                    # Check overlap based on effective sizes
                    if distance < (effective_dot_size + effective_padding):
                        overlaps = True
                        break
                        
                if not overlaps:
                    new_pos = {'left': left, 'top': top}
                    break
                    
                attempts += 1
                
            if new_pos:
                positions.append(new_pos)
            
        return positions
        
    def render_risk_matrix_html(self) -> str:
        """Generate HTML for the risk matrix."""
        matrix_html = '<div class="risk-matrix-container" style="width:100%; margin:0 auto;">'
        
        # Create the grid
        matrix_html += '<div class="risk-matrix-grid" style="display:grid; grid-template-columns:repeat(5, 1fr); aspect-ratio:1; width:100%;">'
        
        # Create a map to store dot positions for each cell
        positions_map = {}
        
        # Generate the grid cells
        for y in range(self.grid_size):
            for x in range(self.grid_size):
                impact = x + 1
                likelihood = self.grid_size - y
                cell_color = self.get_cell_color(impact, likelihood)
                
                # Map cell colors to CSS backgrounds
                bg_color = "#bbf7d0"  # default green
                if cell_color == 'cell-red':
                    bg_color = "#fecaca"
                elif cell_color == 'cell-yellow':
                    bg_color = "#fde68a"
                
                cell_html = f'<div class="risk-cell {cell_color}" style="position:relative; width:100%; aspect-ratio:1; background-color:{bg_color};">'
                
                # Find risks that belong in this cell
                risks_in_cell = [r for r in self.risks_data if r['impact'] == impact and r['likelihood'] == likelihood]
                
                # Generate positions for the dots
                cell_width = 100  # we'll use percentages for positioning
                cell_height = 100
                positions = self.generate_random_positions(len(risks_in_cell), cell_width, cell_height)
                positions_map[f"{x}-{y}"] = positions
                
                # Add dots for risks in this cell
                for i, risk in enumerate(risks_in_cell):
                    if i < len(positions):
                        pos = positions[i]
                        dot_html = f'<div class="risk-dot" style="position:absolute; left:{pos["left"]}%; top:{pos["top"]}%; width:{self.dot_size}%; height:{self.dot_size}%; border-radius:50%; background-color:#212529; color:white; display:flex; align-items:center; justify-content:center; font-weight:600;">{risk["id"]}</div>'
                        cell_html += dot_html
                
                cell_html += '</div>'
                matrix_html += cell_html
                
        matrix_html += '</div>'  # Close grid
        
        # Add axis labels
        matrix_html += '<div style="text-align:center; margin-top:10px;">Impact</div>'
        matrix_html += '</div>'  # Close container
        
        return matrix_html
        
    def render_risk_matrix_svg(self) -> str:
        """Generate SVG for the risk matrix - useful for high-quality vector output in PDF."""
        svg_size = 500  # Size of the SVG
        cell_size = svg_size / self.grid_size
        dot_size = cell_size * 0.18  # 18% of cell size
        
        svg = f'<svg width="{svg_size}" height="{svg_size}" xmlns="http://www.w3.org/2000/svg">'
        
        # Generate the grid cells
        for y in range(self.grid_size):
            for x in range(self.grid_size):
                impact = x + 1
                likelihood = self.grid_size - y
                
                # Calculate cell position
                cell_x = x * cell_size
                cell_y = y * cell_size
                
                # Get cell color
                rgb_color = self.get_cell_color_rgb(impact, likelihood)
                color_hex = f"#{rgb_color[0]:02x}{rgb_color[1]:02x}{rgb_color[2]:02x}"
                
                # Draw cell
                svg += f'<rect x="{cell_x}" y="{cell_y}" width="{cell_size}" height="{cell_size}" fill="{color_hex}" stroke="#fff" stroke-width="1" />'
                
                # Find risks that belong in this cell
                risks_in_cell = [r for r in self.risks_data if r['impact'] == impact and r['likelihood'] == likelihood]
                
                # Generate positions for dots
                positions = self.generate_random_positions(len(risks_in_cell), int(cell_size), int(cell_size))
                
                # Add dots for risks
                for i, risk in enumerate(risks_in_cell):
                    if i < len(positions):
                        pos = positions[i]
                        dot_x = cell_x + pos['left']
                        dot_y = cell_y + pos['top']
                        
                        # Draw dot
                        svg += f'<circle cx="{dot_x + dot_size/2}" cy="{dot_y + dot_size/2}" r="{dot_size/2}" fill="#212529" />'
                        # Add risk ID as text
                        svg += f'<text x="{dot_x + dot_size/2}" y="{dot_y + dot_size/2}" font-size="{dot_size*0.6}" fill="white" text-anchor="middle" dy=".3em">{risk["id"]}</text>'
        
        svg += '</svg>'
        return svg
        
    def render_risk_matrix_png(self, request) -> str:
        """Generate a PNG image of the risk matrix and return as base64 data URI."""
        # Set dimensions
        img_size = 600  # Increase size to accommodate labels
        cell_size = (img_size - 100) // self.grid_size  # Reserve space for labels
        matrix_start_x = 60  # Leave space for Y-axis labels
        matrix_start_y = 20  # Leave space for title
        dot_size = int(cell_size * 0.18)  # 18% of cell size
        
        # Create a new image with white background
        img = Image.new('RGB', (img_size, img_size), color='white')
        draw = ImageDraw.Draw(img)
        
        # Use default font - PIL doesn't handle WOFF files well
        font = None
        try:
            # Try to use a system font if available
            font = ImageFont.load_default()
        except:
            # If even that fails, we'll handle text drawing differently
            pass
        
        # Draw the grid cells
        for y in range(self.grid_size):
            for x in range(self.grid_size):
                impact = x + 1
                likelihood = self.grid_size - y
                
                # Calculate cell position
                cell_x = matrix_start_x + (x * cell_size)
                cell_y = matrix_start_y + (y * cell_size)
                
                # Get cell color
                cell_color = self.get_cell_color_rgb(impact, likelihood)
                
                # Draw cell
                draw.rectangle([cell_x, cell_y, cell_x + cell_size, cell_y + cell_size], 
                               fill=cell_color, outline='white')
                
                # Find risks that belong in this cell
                risks_in_cell = [r for r in self.risks_data if r['impact'] == impact and r['likelihood'] == likelihood]
                
                # Generate positions for dots
                positions = self.generate_random_positions(len(risks_in_cell), cell_size, cell_size)
                
                # Add dots for risks
                for i, risk in enumerate(risks_in_cell):
                    if i < len(positions):
                        pos = positions[i]
                        dot_x = cell_x + int(pos['left'])
                        dot_y = cell_y + int(pos['top'])
                        
                        # Draw dot (circle)
                        draw.ellipse([dot_x, dot_y, dot_x + dot_size, dot_y + dot_size], 
                                    fill='#212529')
                        
                        # Draw risk ID as text
                        risk_id = str(risk["id"])
                        # Calculate text position to center it in the dot
                        if font:
                            try:
                                text_width = draw.textlength(risk_id, font=font) if hasattr(draw, 'textlength') else font.getsize(risk_id)[0]
                                text_x = dot_x + (dot_size - text_width) // 2
                                text_y = dot_y + (dot_size - font.size) // 2
                                draw.text((text_x, text_y), risk_id, fill='white', font=font)
                            except Exception:
                                # If text drawing with font fails, use simple centered text
                                text_x = dot_x + dot_size // 2
                                text_y = dot_y + dot_size // 2
                                draw.text((text_x, text_y), risk_id, fill='white', anchor="mm")
                        else:
                            # If no font available, use centered text with no font specified
                            text_x = dot_x + dot_size // 2
                            text_y = dot_y + dot_size // 2
                            try:
                                draw.text((text_x, text_y), risk_id, fill='white', anchor="mm")
                            except Exception:
                                # Fallback if anchor doesn't work (older Pillow versions)
                                draw.text((dot_x + 2, dot_y + 2), risk_id, fill='white')
        
        # Draw X-axis labels (Impact)
        axis_font_size = 14
        try:
            axis_font = ImageFont.load_default()
        except:
            axis_font = None
            
        # Get localized axis titles
        localizer = request.localizer
        x_axis_title = localizer.translate(_("Impact"))
        y_axis_title = localizer.translate(_("Likelihood"))
            
        # Draw title for X-axis
        draw.text((matrix_start_x + (self.grid_size * cell_size // 2), matrix_start_y + (self.grid_size * cell_size) + 30), 
                 x_axis_title, fill='black', anchor="mm" if hasattr(draw, 'textlength') else None,
                 font=axis_font)
        
        # Draw numbers for X-axis
        for x in range(self.grid_size):
            label = str(x + 1)
            draw.text((matrix_start_x + (x * cell_size) + cell_size // 2, matrix_start_y + (self.grid_size * cell_size) + 10), 
                     label, fill='black', anchor="mm" if hasattr(draw, 'textlength') else None,
                     font=axis_font)
        
        # Draw Y-axis labels (Likelihood)
        # Create rotated text for the Y-axis title
        
        # Method 1: Create a rotated text image and paste it
        try:
            # Create a new image for the rotated text with transparent background
            text_width = 100
            text_height = 20
            text_img = Image.new('RGBA', (text_width, text_height), (255, 255, 255, 0))
            text_draw = ImageDraw.Draw(text_img)
            
            # Draw the text horizontally
            if axis_font:
                if hasattr(text_draw, 'textlength'):
                    title_width = text_draw.textlength(y_axis_title, font=axis_font)
                else:
                    title_width = axis_font.getsize(y_axis_title)[0]
                    
                text_draw.text(((text_width - title_width) // 2, 0), y_axis_title, fill='black', font=axis_font)
            else:
                text_draw.text((text_width // 2, 0), y_axis_title, fill='black')
            
            # Rotate the image 90 degrees
            rotated_text = text_img.rotate(90, expand=True)
            
            # Calculate position for the rotated text
            paste_x = 10
            paste_y = matrix_start_y + (self.grid_size * cell_size // 2) - rotated_text.height // 2
            
            # Paste the rotated text onto the main image
            # We need to create a mask from the alpha channel to preserve transparency
            img.paste(rotated_text, (paste_x, paste_y), rotated_text)
            
        except Exception as e:
            # Fallback to horizontal text if rotation fails
            print(f"Error creating rotated text: {e}")
            draw.text((matrix_start_x - 40, matrix_start_y + (self.grid_size * cell_size // 2) - 50), 
                     y_axis_title, fill='black', anchor="mm" if hasattr(draw, 'textlength') else None,
                     font=axis_font)
        
        # Draw numbers for Y-axis
        for y in range(self.grid_size):
            label = str(self.grid_size - y)  # Reverse order
            draw.text((matrix_start_x - 10, matrix_start_y + (y * cell_size) + cell_size // 2), 
                     label, fill='black', anchor="mm" if hasattr(draw, 'textlength') else None,
                     font=axis_font)
                 
        # Convert the image to a data URI
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        img_str = b64encode(buffer.getvalue()).decode('ascii')
        data_uri = f'data:image/png;base64,{img_str}'
        
        return data_uri


def download_report_view(context: "Organization", request: "IRequest") -> Response:
    """Generate and download a PDF report of the risk assessment."""
    # Get the latest risk assessment info
    latest_assessment = (
        request.dbsession.query(RiskAssessmentInfo)
        .filter(RiskAssessmentInfo.organization_id == context.id)
        .order_by(RiskAssessmentInfo.created.desc())
        .first()
    )

    if not latest_assessment:
        request.session.flash(_("No risk assessment found"), "error")
        return Response(status=404)

    # Get all risks for this assessment with proper joins
    risks = (
        request.dbsession.query(RiskAssessment)
        .join(RiskAssessment.risk)  # Join with risk table
        .outerjoin(RiskAssessment.treatment)  # Outer join with treatment since it's optional
        .options(
            joinedload(RiskAssessment.risk),
            joinedload(RiskAssessment.treatment)
        )
        .filter(
            RiskAssessment.organization_id == context.id,
            RiskAssessment.risk_assessment_info_id == latest_assessment.id
        )
        .distinct()  # Ensure we don't get duplicates
        .all()
    )

    # Convert risks to the format expected by our template
    risks_data = []
    for i, risk in enumerate(risks, start=1):
        # Make sure we have valid impact and likelihood values
        impact = 0
        likelihood = 0
        
        try:
            if hasattr(risk, 'impact') and risk.impact is not None:
                impact = int(risk.impact)
        except (ValueError, TypeError):
            pass
            
        try:
            if hasattr(risk, 'likelihood') and risk.likelihood is not None:
                likelihood = int(risk.likelihood)
        except (ValueError, TypeError):
            pass
            
        # Only include risks with valid impact and likelihood values (1-5)
        if 1 <= impact <= 5 and 1 <= likelihood <= 5:
            # Get the first treatment if multiple exist
            treatment = None
            if hasattr(risk, 'treatment'):
                treatment = risk.treatment[0] if isinstance(risk.treatment, list) and risk.treatment else risk.treatment
                
            risks_data.append({
                'id': i,  # Use sequential numbering
                'name': risk.name if hasattr(risk, 'name') else f"Risk {i}",
                'impact': impact,
                'likelihood': likelihood,
                'treatment': treatment.description if treatment and hasattr(treatment, 'description') else None,
                'treatment_type': str(treatment.treatment_type) if treatment and hasattr(treatment, 'treatment_type') else None,
                'treatment_details': treatment.description if treatment and hasattr(treatment, 'description') else None,
            })
    
    # Print distribution for debugging
    impact_likelihood_counts = {}
    for risk in risks_data:
        key = (risk['impact'], risk['likelihood'])
        if key not in impact_likelihood_counts:
            impact_likelihood_counts[key] = 0
        impact_likelihood_counts[key] += 1
        
    print(f"Report contains {len(risks_data)} risks with the following distribution:")
    for impact in range(1, 6):
        for likelihood in range(1, 6):
            key = (impact, likelihood)
            count = impact_likelihood_counts.get(key, 0)
            if count > 0:
                print(f"Impact {impact}, Likelihood {likelihood}: {count} risks")

    # Create view instance with the risks data
    view = ReportView(risks_data)
    
    # Generate the risk matrix visualization
    risk_matrix_image = view.render_risk_matrix_png(request)

    # Prepare data for the report template
    report_data = {
        'organization': context,
        'assessment': latest_assessment,
        'risks': risks_data,
        'view': view,
        'request': request,
        'layout': request.layout_manager.layout,
        'risk_matrix_image': risk_matrix_image,  # Pass the generated risk matrix image
    }

    # Determine the template based on locale
    locale = request.locale_name
    # Map locale to template file
    template_map = {
        'de': 'templates/reports/report_de.pt',
        'fr': 'templates/reports/report_fr.pt',
        'en': 'templates/reports/report_en.pt',
    }
    # Default to English if locale not found
    template_name = template_map.get(locale, 'templates/reports/report_en.pt')

    # Render the HTML template
    html_content = render(
        template_name,
        report_data,
        request=request
    )

    # Add custom CSS for PDF rendering
    pdf_css = CSS(string='''
        @page {
            size: A4;
            margin: 2.5cm;
            @bottom-right {
                content: counter(page);
            }
        }
    ''')

    # Render the HTML content to a document then generate PDF bytes
    document = HTML(string=html_content).render(stylesheets=[pdf_css])
    pdf_bytes = document.write_pdf()

    # Prepare the response using the generated PDF bytes
    response = Response(content_type='application/pdf', body=pdf_bytes)
    response.content_length = len(pdf_bytes)
    filename = f"risk-assessment-{latest_assessment.created.strftime('%Y-%m-%d')}.pdf"
    response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    return response


# Test function for generating a risk matrix image for development/debugging purposes
def generate_test_risk_matrix(request):
    """Generate a test risk matrix image and save it to a file."""
    # Generate sample risk data with some dots for each level 1-5
    risks_data = []
    
    # Ensure we have at least one risk at each impact and likelihood level
    for impact in range(1, 6):
        for likelihood in range(1, 6):
            risks_data.append({
                'id': len(risks_data) + 1,
                'name': f'Test Risk I:{impact} L:{likelihood}',
                'impact': impact,
                'likelihood': likelihood,
            })
    
    # Add some more random risks
    for i in range(len(risks_data) + 1, 40):
        risks_data.append({
            'id': i,
            'name': f'Test Risk {i}',
            'impact': random.randint(1, 5),
            'likelihood': random.randint(1, 5),
        })
    
    # Print the distribution of risks for debugging
    print("Risk distribution:")
    impact_likelihood_counts = {}
    for risk in risks_data:
        key = (risk['impact'], risk['likelihood'])
        if key not in impact_likelihood_counts:
            impact_likelihood_counts[key] = 0
        impact_likelihood_counts[key] += 1
    
    for impact in range(1, 6):
        for likelihood in range(1, 6):
            key = (impact, likelihood)
            count = impact_likelihood_counts.get(key, 0)
            print(f"Impact {impact}, Likelihood {likelihood}: {count} risks")
    
    # Create view instance with the risks data
    view = ReportView(risks_data)
    
    # Generate the risk matrix image
    data_uri = view.render_risk_matrix_png(request)
    
    # Extract base64 image data from the data URI
    img_data = data_uri.split('base64,')[1]
    
    # Decode and save to a file
    img_bytes = b64encode(b64decode(img_data))
    with open('/tmp/test_risk_matrix.png', 'wb') as f:
        f.write(b64decode(img_data))
    
    return Response(f"Test risk matrix generated and saved to /tmp/test_risk_matrix.png. Risk count: {len(risks_data)}") 