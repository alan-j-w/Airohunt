# Airohunt AI — Career Discovery & Opportunity Intelligence Platform

Airohunt AI is a local-first, profile-driven Career Discovery Platform designed to help job seekers discover better opportunities, eliminate low-quality listings, and improve interview conversion rates through intelligent validation, ranking, and application optimization.

Unlike traditional job boards that prioritize quantity, Airohunt focuses on quality. The platform aggregates opportunities from multiple sources, removes duplicates, filters scams and training institutes, validates opportunities against user-defined requirements, and surfaces only the most relevant jobs.

The core philosophy behind Airohunt is simple:

> **The goal is not to apply to more jobs. The goal is to find better jobs and secure more interviews.**

---

## Why Airohunt Exists

Airohunt was originally built from a real-world problem faced by a fresher software developer.

Modern job boards are often filled with:

* Duplicate listings
* Training institutes disguised as employers
* Placement agencies and consultancies
* Course-selling organizations
* Outdated vacancies
* Irrelevant opportunities
* Low-quality job aggregations

Finding genuine opportunities often requires manually filtering hundreds of listings every week.

Airohunt was created to automate that filtering process while maintaining transparency and user control.

Instead of showing every available job, Airohunt attempts to answer a more important question:

> **Which opportunities are actually worth my time?**

---

# Core Features

## Strict Job Validation Engine

Every collected job passes through a validation pipeline that evaluates:

* Role compatibility
* Skill alignment
* Experience requirements
* Location preferences
* Salary expectations
* Company type preferences
* Authenticity indicators

Each job receives a validation score and is classified into:

### Tier A — Excellent Match

★★★★★

High-confidence opportunities closely aligned with the candidate profile.

### Tier B — Strong Match

★★★★☆

Relevant opportunities with minor tradeoffs.

### Tier C — Possible Match

★★★☆☆

Potential opportunities that may require manual review.

### Tier D — Rejected

Automatically hidden listings that fail validation rules.

---

## Scam & Low-Quality Listing Detection

Airohunt automatically identifies and filters:

* Training institutes
* Placement consultancies
* Course sellers
* Pay-to-join programs
* Bond-based opportunities
* Known blacklisted organizations
* Listings with missing critical information

This significantly reduces noise in the job discovery process.

---

## Duplicate Intelligence

The platform detects identical vacancies appearing across multiple job sources and retains only the highest-quality version.

Source priority example:

```text
Company Careers Page
        ↓
Greenhouse / Lever
        ↓
Ashby / Workable
        ↓
Jooble / Adzuna
        ↓
Unknown Aggregators
```

This prevents candidates from wasting time reviewing the same vacancy multiple times.

---

## Validation Confidence System

Every listing receives a confidence score based on available information:

* Salary transparency
* Description quality
* Company information
* Application link quality

This allows users to quickly identify trustworthy opportunities.

---

## Career Memory Engine

Airohunt learns from real application outcomes.

Over time, the system tracks:

* Applications submitted
* Interview invitations
* Offers received
* Successful resume versions
* High-performing job sources

These signals help prioritize future opportunities based on actual results rather than assumptions.

---

## Resume Version Management

Users can maintain multiple specialized resumes:

* React Developer
* MERN Stack Developer
* Django Developer
* Full Stack Developer
* Cybersecurity Analyst

The system automatically selects the most appropriate version before tailoring.

---

## ATS Resume Tailoring

Airohunt can optimize resumes using either:

* Local heuristic engines
* OpenAI
* Groq
* Gemini

The tailoring process focuses on:

* ATS keyword alignment
* Relevant skill emphasis
* Role-specific summaries
* Professional formatting

while avoiding fabricated experience or credentials.

---

## Application Assistant

Airohunt assists candidates during the application process through:

* ATS platform detection
* Application preparation
* Console autofill script generation
* Application queue management
* Submission tracking

Supported platforms include:

* Greenhouse
* Lever
* Ashby
* Workable
* SmartRecruiters

---

## Automation Canvas

The Automation Canvas provides a visual workflow builder allowing users to customize:

```text
Job Sources
↓
Validation Engine
↓
Filtering Rules
↓
Scoring Logic
↓
Resume Tailoring
↓
Application Preparation
```

without modifying application code.

---

# Architecture Overview

```text
Job Sources
↓
Duplicate Intelligence
↓
Strict Validation Engine
↓
Scam Detection
↓
Source Quality Ranking
↓
Career Memory Engine
↓
Opportunity Ranking
↓
Resume Selection
↓
ATS Tailoring
↓
Application Queue
↓
Application Assistant
```

---

# Technology Stack

## Backend

* Python 3.12+
* FastAPI
* Pydantic
* Uvicorn

## Frontend

* React 18
* Zustand
* React Flow
* TailwindCSS

## AI Providers

* OpenAI
* Groq
* Gemini
* Local Heuristic Engines

---

# Project Vision

Airohunt is not intended to become another job board.

The long-term vision is to build a transparent and explainable Career Operating System that helps users:

* Discover higher-quality opportunities
* Reduce exposure to scams and low-value listings
* Improve application quality
* Learn from hiring outcomes
* Make better career decisions using real data

Every recommendation should be explainable.

Every ranking should be measurable.

Every opportunity should earn its place in the feed.

---

# Open Source & License

Created and maintained by **Alan Joy Wilson**.

This project was built from personal job-search challenges and is being developed as an open-source effort to help candidates navigate modern hiring more effectively.

Copyright © 2026 Alan Joy Wilson

## License

License: To Be Determined (TBD)

Airohunt is currently an active personal project and career experiment.

The licensing model will be finalized after validation and public release.
> Find fewer jobs. Find better jobs. Get more interviews.
