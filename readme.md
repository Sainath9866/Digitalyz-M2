# Course Scheduling System
visit : https://github.com/Sainath9866/Digitalyz-M2 to get more screenshots 

A sophisticated course scheduling system that optimizes class assignments while considering various constraints using linear programming. The system creates efficient schedules for students, teachers, and rooms across multiple terms.

## Overview

This system solves the complex problem of academic course scheduling by:
- Assigning courses to time blocks and rooms
- Managing student course requests and preferences
- Handling teacher availability and constraints
- Optimizing room utilization
- Ensuring no scheduling conflicts

## Features

- **Multi-Term Scheduling**: Supports scheduling across multiple terms
- **Flexible Time Blocks**: Three blocks per day (Morning, Afternoon, Evening)
- **Constraint Handling**:
  - Room capacity limits
  - Teacher availability
  - Course prerequisites
  - Student preferences
  - Minimum/maximum section sizes
- **Interactive Schedule Viewer**: Web interface to view schedules by:
  - Room
  - Course
  - Student
- **Comprehensive Statistics**:
  - Room utilization rates
  - Section size distribution
  - Term-wise summaries

## Technical Approach

### 1. Time Block Structure

We implemented a week-wise scheduling approach with 3 blocks per day because:
- Each block needs to be 90-120 minutes (course requirement)
- Students need adequate breaks between classes
- Teachers need preparation time
- A day-wise approach with 7 blocks would:
  - Violate the 90-120 minute requirement
  - Be physically and mentally exhausting
  - Not allow for proper breaks
  - Compromise learning effectiveness

### 2. Optimization Model

The system uses Linear Programming (PuLP library) to:
- Maximize satisfied course requests
- Prioritize core courses
- Balance section sizes
- Minimize room conflicts
- Ensure teacher availability

Key Decision Variables:
- Student-Course-Term assignments
- Course-Block-Term scheduling
- Room assignments

### 3. Constraint Handling

The system manages multiple constraints:
1. **Student Constraints**:
   - Maximum courses per term
   - No scheduling conflicts
   - Course prerequisites

2. **Teacher Constraints**:
   - No double booking
   - Preferred teaching blocks
   - Maximum teaching load

3. **Room Constraints**:
   - Capacity limits
   - Special requirements (labs, etc.)
   - No double booking

4. **Course Constraints**:
   - Minimum/maximum section sizes
   - Required number of sections
   - Specific room requirements

## Technologies Used

- **Python**: Primary programming language
- **PuLP**: Linear programming solver
- **Pandas**: Data manipulation and analysis
- **NumPy**: Numerical computations
- **Streamlit**: Web interface
- **Excel**: Data input format

## Installation

1. Clone the repository
2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

1. Prepare your data in the Excel format (see `cleaned_dataset.xlsx`)
2. Run the scheduler:
```bash
python main.py
```
3. View the schedules:
```bash
streamlit run app.py
```

## Data Requirements

The system expects an Excel file with these sheets:
1. **Lecturer Details**: Teacher information and course assignments
2. **Rooms Data**: Room capacities and restrictions
3. **Course List**: Course information and constraints
4. **Student Requests**: Student course preferences

## Output

The system generates:
1. Complete course schedule
2. Room utilization statistics
3. Section size distribution
4. Term summaries
5. Individual schedules for:
   - Students
   - Teachers
   - Rooms

## Performance Optimization

The system includes several optimizations:
1. Pre-processing of course requests
2. Simplified block structure
3. Efficient constraint formulation
4. Solver parameter tuning
5. Memory usage optimization

## Limitations and Future Improvements

Current limitations:
1. Fixed block structure
2. Limited support for course prerequisites
3. No automatic handling of teacher preferences

Planned improvements:
1. Dynamic block sizing
2. Enhanced preference handling
3. More sophisticated room assignment
4. Additional visualization options

## Contributing

Contributions are welcome! Please read the contributing guidelines before submitting pull requests.



## Acknowledgments

- PuLP library for linear programming
- Streamlit for the web interface

