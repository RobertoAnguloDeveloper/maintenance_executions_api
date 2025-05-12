# Form Submission Export API Documentation

This document outlines all available API endpoints for exporting form submissions to PDF and DOCX formats, with both default and custom styling options.

> **Note:** Replace `{submission_id}` in all URLs with the actual submission ID you want to export.

## Authentication

All endpoints require authentication via JWT token. Include the token in the Authorization header:

```
Authorization: Bearer <your_jwt_token>
```

## Table of Contents

- [Customization Options](#customization-options)
- [PDF Exports](#pdf-exports)
  - [Default PDF Export](#default-pdf-export)
  - [Custom PDF Export](#custom-pdf-export)
- [DOCX Exports](#docx-exports)
  - [Default DOCX Export](#default-docx-export)
  - [Custom DOCX Export](#custom-docx-export)
- [Parameter Details](#parameter-details)
- [Sample cURL Commands](#sample-curl-commands)
- [Example Style Configurations](#example-style-configurations)

## Customization Options

Get a list of all available customization options for exports.

### Request

```
GET /api/export_submissions/customization_options
```

This endpoint provides details about all available customization parameters for both PDF and DOCX exports.

## PDF Exports

### Default PDF Export

Export a form submission as PDF with default styling.

#### Request

```
GET /api/export_submissions/{submission_id}/pdf
```

### Custom PDF Export

Export a form submission as PDF with custom styling and options.

#### Request URL

```
POST /api/export_submissions/{submission_id}/pdf/custom
```

> **Note:** This is a `multipart/form-data` request to allow file uploads.

#### Request Body (multipart/form-data)

Common parameters:

```
header_image: [FILE]
header_opacity: 80
header_size: 50
header_width: 200
header_height: 100
header_alignment: center
signatures_size: 80
signatures_alignment: vertical
include_signatures: true
```

Style options (examples):

```
title_font_family: Helvetica-Bold
title_font_size: 18
title_font_color: #000000
title_alignment: CENTER
title_space_after: 0.25
info_font_family: Helvetica
info_font_size: 10
info_font_color: #2F4F4F
info_label_font_family: Helvetica-Bold
info_space_after: 0.2
question_font_family: Helvetica-Bold
question_font_size: 11
question_font_color: #000000
question_left_indent: 0
question_space_before: 0.15
question_space_after: 4
question_leading: 14
answer_font_family: Helvetica
answer_font_size: 10
answer_font_color: #2F4F4F
answer_left_indent: 15
answer_space_before: 2
answer_space_after: 0.15
answer_leading: 12
qa_layout: answer_below
answer_same_line_max_length: 70
table_header_font_family: Helvetica-Bold
table_header_font_size: 9
table_header_font_color: #000000
table_header_bg_color: #D3D3D3
table_header_padding: 3
table_header_alignment: CENTER
table_cell_font_family: Helvetica
table_cell_font_size: 8
table_cell_font_color: #000000
table_cell_padding: 3
table_cell_alignment: LEFT
table_grid_color: #808080
table_grid_thickness: 0.5
signature_label_font_family: Helvetica-Bold
signature_label_font_size: 12
signature_label_font_color: #000000
signature_text_font_family: Helvetica
signature_text_font_size: 9
signature_text_font_color: #000000
signature_image_width: 2.0
signature_image_height: 0.8
signature_section_space_before: 0.3
signature_space_between_vertical: 0.2
```

## DOCX Exports

### Default DOCX Export

Export a form submission as DOCX with default styling.

#### Request

```
GET /api/export_submissions/{submission_id}/docx
```

### Custom DOCX Export

Export a form submission as DOCX with custom styling and options.

#### Request URL

```
POST /api/export_submissions/{submission_id}/docx/custom
```

> **Note:** This is a `multipart/form-data` request to allow file uploads.

#### Request Body (multipart/form-data)

Common parameters:

```
header_image: [FILE]
header_size: 50
header_width: 200
header_height: 100
header_alignment: center
signatures_size: 80
signatures_alignment: vertical
include_signatures: true
```

Style options (examples):

```
title_font_family: Arial
title_font_size: 18
title_font_color: #000000
title_alignment: CENTER
title_space_after: 0.25
info_font_family: Arial
info_font_size: 10
info_font_color: #2F4F4F
info_label_font_family: Arial
info_space_after: 0.2
question_font_family: Arial
question_font_size: 11
question_font_color: #000000
question_left_indent: 0
question_space_before: 0.15
question_space_after: 4
question_leading: 14
answer_font_family: Arial
answer_font_size: 10
answer_font_color: #2F4F4F
answer_left_indent: 15
answer_space_before: 2
answer_space_after: 0.15
answer_leading: 12
qa_layout: answer_below
answer_same_line_max_length: 70
table_header_font_family: Arial
table_header_font_size: 9
table_header_font_color: #000000
table_header_bg_color: #D3D3D3
table_header_alignment: CENTER
table_cell_font_family: Arial
table_cell_font_size: 8
table_cell_font_color: #000000
table_cell_alignment: LEFT
signature_label_font_family: Arial
signature_label_font_size: 12
signature_label_font_color: #000000
signature_text_font_family: Arial
signature_text_font_size: 9
signature_text_font_color: #000000
signature_section_space_before: 0.3
signature_space_between_vertical: 0.2
```

## Parameter Details

### Common Parameters

| Parameter | Type | Description | Example |
|-----------|------|-------------|---------|
| header_image | File | Image to display at the top of the document | PNG, JPG, JPEG, SVG file |
| header_opacity | Float | Opacity of header image (0-100, PDF only) | 80 |
| header_size | Float | Size percentage of original image dimensions | 50 |
| header_width | Float | Specific width in pixels (overrides header_size) | 200 |
| header_height | Float | Specific height in pixels (overrides header_size) | 100 |
| header_alignment | String | Horizontal alignment of header image | "left", "center", "right" |
| signatures_size | Float | Size percentage of signature images | 80 |
| signatures_alignment | String | Layout for multiple signatures | "vertical", "horizontal" |
| include_signatures | Boolean | Whether to include signatures | true, false |

### Style Parameters

| Parameter | Type | Description | PDF Example | DOCX Example |
|-----------|------|-------------|------------|--------------|
| title_font_family | String | Font family for document title | "Helvetica-Bold" | "Arial" |
| title_font_size | Float | Font size for document title | 18 | 18 |
| title_font_color | String | Color for document title | "#000000" | "#000000" |
| title_alignment | String | Alignment for document title | "CENTER" | "CENTER" |
| qa_layout | String | Layout for questions and answers | "answer_below", "answer_same_line" | Same |
| page_margin_top | Float | Top margin in inches | 0.75 | 0.75 |
| page_margin_bottom | Float | Bottom margin in inches | 0.75 | 0.75 |
| page_margin_left | Float | Left margin in inches | 0.75 | 0.75 |
| page_margin_right | Float | Right margin in inches | 0.75 | 0.75 |

> **Note:** For the full list of style parameters, use the `/api/export_submissions/customization_options` endpoint.

## Example Style Configurations

### Minimal Custom Style (Light Theme)

A minimal style configuration for a light theme:

```
title_font_family: Helvetica-Bold
title_font_size: 20
title_font_color: #336699
title_alignment: CENTER
question_font_family: Helvetica-Bold
question_font_size: 12
question_font_color: #336699
answer_font_family: Helvetica
answer_font_size: 11
answer_font_color: #333333
qa_layout: answer_same_line
```

### Corporate Style (Dark Headers)

A style configuration with dark headers suitable for corporate documents (works for both PDF and DOCX by using compatible font specifications):

```
title_font_family: Arial
title_font_size: 18
title_font_color: #FFFFFF
title_alignment: LEFT
title_space_after: 0.3
page_margin_top: 1.0
page_margin_bottom: 1.0
page_margin_left: 1.0
page_margin_right: 1.0
question_font_family: Arial-Bold
question_font_size: 11
question_font_color: #003366
answer_font_family: Arial
answer_font_size: 10
answer_font_color: #333333
table_header_font_family: Arial-Bold
table_header_font_size: 10
table_header_font_color: #FFFFFF
table_header_bg_color: #003366
table_cell_font_family: Arial
table_cell_font_size: 9
table_cell_font_color: #333333
table_grid_color: #CCCCCC
qa_layout: answer_below
```

### Sample cURL Commands

Here are sample cURL commands for each endpoint:

#### Get Customization Options

```bash
curl -X GET "https://yourapi.example.com/api/export_submissions/customization_options" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

#### Default PDF Export

```bash
curl -X GET "https://yourapi.example.com/api/export_submissions/123/pdf" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  --output "submission.pdf"
```

#### Custom PDF Export

```bash
curl -X POST "https://yourapi.example.com/api/export_submissions/123/pdf/custom" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -F "header_image=@/path/to/logo.png" \
  -F "header_size=50" \
  -F "header_alignment=center" \
  -F "signatures_alignment=horizontal" \
  -F "title_font_family=Helvetica-Bold" \
  -F "title_font_size=20" \
  -F "title_font_color=#336699" \
  -F "answer_font_color=#333333" \
  --output "custom_submission.pdf"
```

#### Default DOCX Export

```bash
curl -X GET "https://yourapi.example.com/api/export_submissions/123/docx" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  --output "submission.docx"
```

#### Custom DOCX Export

```bash
curl -X POST "https://yourapi.example.com/api/export_submissions/123/docx/custom" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -F "header_image=@/path/to/logo.png" \
  -F "header_size=50" \
  -F "header_alignment=center" \
  -F "signatures_alignment=horizontal" \
  -F "title_font_family=Arial" \
  -F "title_font_size=20" \
  -F "title_font_color=#336699" \
  -F "answer_font_color=#333333" \
  --output "custom_submission.docx"
```

### Accessible Style (High Contrast)

A high-contrast style configuration for improved accessibility:

```
title_font_family: Helvetica-Bold
title_font_size: 22
title_font_color: #000000
title_alignment: CENTER
question_font_family: Helvetica-Bold
question_font_size: 14
question_font_color: #000000
answer_font_family: Helvetica
answer_font_size: 14
answer_font_color: #000000
table_header_font_family: Helvetica-Bold
table_header_font_size: 12
table_header_font_color: #FFFFFF
table_header_bg_color: #000000
table_cell_font_family: Helvetica
table_cell_font_size: 12
table_cell_font_color: #000000
table_grid_color: #000000
table_grid_thickness: 1.0
qa_layout: answer_below
```

### Compact Style

A style configuration optimized for compact documents with minimal spacing:

```
title_font_family: Times-Roman
title_font_size: 16
title_space_after: 0.15
question_font_family: Times-Bold
question_font_size: 10
question_space_before: 0.08
question_space_after: 2
answer_font_family: Times-Roman
answer_font_size: 10
answer_left_indent: 10
answer_space_before: 0
answer_space_after: 0.08
qa_layout: answer_same_line
answer_same_line_max_length: 100
table_header_font_size: 8
table_cell_font_size: 8
table_cell_padding: 2
signature_image_width: 1.5
signature_image_height: 0.6
signature_space_between_vertical: 0.1
```
