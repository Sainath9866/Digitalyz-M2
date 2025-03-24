import pandas as pd
import numpy as np
import pulp
from collections import defaultdict
from typing import Dict, List, Tuple, Any
import pickle

class CourseScheduler:
    def __init__(self, lecturer_data: pd.DataFrame, rooms_data: pd.DataFrame, 
                 course_data: pd.DataFrame, student_requests: pd.DataFrame):
        """Initialize the course scheduler with input data and process relationships"""
        self.lecturer_data = lecturer_data
        self.rooms_data = rooms_data
        self.course_data = course_data
        self.student_requests = student_requests
        
        # Define time blocks and terms
        self.days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
        self.daily_blocks = ['Morning', 'Afternoon', 'Evening']  # Each 90-120 minutes
        self.blocks = [f"{day}-{block}" for day in self.days for block in self.daily_blocks]
        self.terms = [1, 2]
        
        # Process core data
        self.students = sorted(list(set(student_requests['student_id'])))
        self.courses = {row['course_code']: row for _, row in course_data.iterrows()}
        
        # Create lecturer list
        self.lecturer_ids = sorted(list(set(lecturer_data['lecturer_id'])))
        
        # Clean up available blocks in course data
        for course in self.courses.values():
            if pd.isna(course['available_blocks']):
                course['available_blocks'] = ', '.join(self.blocks)
            else:
                # Clean and standardize block names
                blocks = course['available_blocks'].split(', ')
                cleaned_blocks = []
                for block in blocks:
                    for day in self.days:
                        for time in self.daily_blocks:
                            if f"{day}-{time}" == block:
                                cleaned_blocks.append(block)
                course['available_blocks'] = ', '.join(cleaned_blocks) if cleaned_blocks else ', '.join(self.blocks)
        
        # Process relationships
        self.teacher_courses = self._process_teacher_courses()
        self.room_assignments = self._process_room_assignments()
        self.course_terms = self._process_course_terms()
        self.student_course_requests = self._process_student_requests()

    def _process_teacher_courses(self) -> Dict[str, List[str]]:
        """Map teachers to their assigned courses"""
        teacher_courses = defaultdict(list)
        for _, row in self.lecturer_data.iterrows():
            teacher_courses[row['lecturer_id']].append(row['lecture_code'])
        return teacher_courses

    def _process_room_assignments(self) -> Dict[Tuple[str, int], str]:
        """Map course sections to their required rooms"""
        room_assignments = {}
        for _, row in self.rooms_data.iterrows():
            room_assignments[(row['course_code'], int(row['section_number']))] = str(row['room_number'])
        return room_assignments

    def _process_course_terms(self) -> Dict[str, Dict[str, Any]]:
        """Process course term information"""
        course_terms = {}
        for _, row in self.lecturer_data.iterrows():
            course_terms[row['lecture_code']] = {
                'start_term': row['start_term'],
                'length': row['length']
            }
        return course_terms

    def _process_student_requests(self) -> Dict[str, List[Tuple[str, str]]]:
        """Process student course requests with priorities"""
        requests = defaultdict(list)
        for _, row in self.student_requests.iterrows():
            requests[row['student_id']].append((row['course_code'], row['priority']))
        return requests

    def create_schedule(self):
        """Create an optimal course schedule using linear programming"""
        # Initialize the model
        model = pulp.LpProblem("Course_Scheduling", pulp.LpMaximize)
        
        # Get unique rooms from room assignments and rooms data
        rooms = sorted(set(str(room) for room in self.rooms_data['room_number'].unique()))
        
        print(f"Number of students: {len(self.students)}")
        print(f"Number of courses: {len(self.courses)}")
        print(f"Number of rooms: {len(rooms)}")
        print(f"Number of blocks per term: {len(self.blocks)}")
        
        # Pre-compute course data and reduce problem size
        course_requests = defaultdict(int)
        course_students = defaultdict(set)
        for s in self.students:
            for c, _ in self.student_course_requests[s]:
                if c in self.courses:
                    course_requests[c] += 1
                    course_students[c].add(s)
        
        # Only consider courses with actual requests
        active_courses = {c: course for c, course in self.courses.items() if c in course_requests}
        
        print("\nTop requested courses:")
        for course, count in sorted(course_requests.items(), key=lambda x: x[1], reverse=True)[:5]:
            print(f"{course}: {count} requests, {self.courses[course]['number_of_sections']} sections")
        
        # Reduce time blocks - group by day instead of specific times
        simplified_blocks = list(set(block.split('-')[0] for block in self.blocks))  # Just use days
        print(f"\nUsing {len(simplified_blocks)} time blocks per term")
        
        # Pre-compute valid student-course pairs
        valid_student_courses = {(s, c) for s in self.students 
                               for c, _ in self.student_course_requests[s] 
                               if c in active_courses}
        
        print("\nCreating decision variables...")
        
        # x[student, course, term] = 1 if student is assigned to course in term
        x = pulp.LpVariable.dicts("student_assignment",
                                [(s, c, t)
                                 for (s, c) in valid_student_courses
                                 for t in self.terms],
                                cat=pulp.LpBinary)
        
        # y[course, block, term] = 1 if course is scheduled in block
        y = pulp.LpVariable.dicts("course_scheduled",
                                [(c, b, t)
                                 for c in active_courses
                                 for b in simplified_blocks
                                 for t in self.terms],
                                cat=pulp.LpBinary)
        
        print("Decision variables created.")
        
        # OBJECTIVE: Maximize satisfied requests
        print("\nSetting up objective function...")
        model += pulp.lpSum(x[s, c, t] * (100 if active_courses[c]['priority'] == 'Core course' else 50)
                          for (s, c) in valid_student_courses
                          for t in self.terms)
        
        # CONSTRAINTS
        print("\nSetting up constraints...")
        
        # 1. Each student can only take a course once
        for s, c in valid_student_courses:
            model += pulp.lpSum(x[s, c, t] for t in self.terms) <= 1
        
        # 2. Course capacity constraints
        for c in active_courses:
            max_students = active_courses[c]['maximum_section_size'] * int(active_courses[c]['number_of_sections'])
            for t in self.terms:
                model += pulp.lpSum(x[s, c2, t] for s, c2 in valid_student_courses if c2 == c) <= max_students
        
        # 3. Each course needs at least minimum students to run
        for c in active_courses:
            min_students = max(1, active_courses[c]['minimum_section_size'] - 2)
            for t in self.terms:
                scheduled = pulp.lpSum(y[c, b, t] for b in simplified_blocks)
                enrolled = pulp.lpSum(x[s, c2, t] for s, c2 in valid_student_courses if c2 == c)
                model += enrolled >= min_students * scheduled
                model += enrolled <= 1000 * scheduled  # Big M constraint
        
        # 4. Each course can only be scheduled once per day
        for c in active_courses:
            for t in self.terms:
                model += pulp.lpSum(y[c, b, t] for b in simplified_blocks) <= int(active_courses[c]['number_of_sections'])
        
        # 5. Teacher conflicts
        for teacher_id, courses in self.teacher_courses.items():
            teacher_active_courses = [c for c in courses if c in active_courses]
            if teacher_active_courses:
                for b in simplified_blocks:
                    for t in self.terms:
                        model += pulp.lpSum(y[c, b, t] for c in teacher_active_courses) <= 1
        
        # Solve with aggressive parameters
        print("\nSolving with simplified model...")
        solver = pulp.PULP_CBC_CMD(
            timeLimit=120,  # 2 minutes max
            gapRel=0.1,    # Accept solutions within 10% of optimal
            threads=4,
            msg=1
        )
        status = model.solve(solver)
        
        print(f"\nStatus: {pulp.LpStatus[status]}")
        if status == pulp.LpStatusOptimal:
            print(f"Objective Value: {pulp.value(model.objective)}")
        
        # Extract schedule
        schedule = self._extract_simplified_schedule(x, y, simplified_blocks, active_courses, valid_student_courses)
        statistics = self._generate_statistics(schedule, rooms)
        return schedule, statistics

    def _extract_simplified_schedule(self, x, y, blocks, active_courses, valid_student_courses):
        """Extract schedule from simplified model"""
        schedule = {
            'student_schedules': {},
            'course_sections': {},
            'room_schedules': {}
        }
        
        # Initialize nested dictionaries
        for student in self.students:
            schedule['student_schedules'][student] = {'term1': {}, 'term2': {}}
        
        for course in active_courses:
            schedule['course_sections'][course] = {'term1': [], 'term2': []}
        
        # Initialize room schedules
        available_rooms = sorted(set(str(room) for room in self.rooms_data['room_number'].unique()))
        for room in available_rooms:
            schedule['room_schedules'][room] = {'term1': {}, 'term2': {}}
        
        # Assign rooms round-robin style
        room_idx = 0
        
        # Extract assignments
        for c in active_courses:
            for t in self.terms:
                for b in blocks:
                    if (c, b, t) in y and pulp.value(y[c, b, t]) == 1:
                        # Count students in this section
                        enrolled_students = sum(1 for (s, c2) in valid_student_courses 
                                             if c2 == c and (s, c, t) in x 
                                             and pulp.value(x[s, c, t]) == 1)
                        
                        # Assign room round-robin
                        assigned_room = available_rooms[room_idx]
                        room_idx = (room_idx + 1) % len(available_rooms)
                        
                        # Add to course sections
                        schedule['course_sections'][c][f'term{t}'].append({
                            'section': 1,
                            'block': f"{b}-Morning",
                            'room': assigned_room,
                            'students': enrolled_students
                        })
                        
                        # Add to room schedule
                        if f"{b}-Morning" not in schedule['room_schedules'][assigned_room][f'term{t}']:
                            schedule['room_schedules'][assigned_room][f'term{t}'][f"{b}-Morning"] = []
                        schedule['room_schedules'][assigned_room][f'term{t}'][f"{b}-Morning"].append({
                            'course': c,
                            'section': 1,
                            'students': enrolled_students
                        })
        
        # Extract student schedules
        for s, c in valid_student_courses:
            for t in self.terms:
                if (s, c, t) in x and pulp.value(x[s, c, t]) == 1:
                    # Find which block this course was scheduled in
                    for b in blocks:
                        if (c, b, t) in y and pulp.value(y[c, b, t]) == 1:
                            schedule['student_schedules'][s][f'term{t}'][f"{b}-Morning"] = {
                                'course': c,
                                'section': 1,
                                'title': active_courses[c]['title']
                            }
        
        return schedule

    def _generate_statistics(self, schedule, rooms):
        """Generate comprehensive statistics about the schedule"""
        stats = {
            'room_utilization': self._calculate_room_utilization(schedule, rooms),
            'section_sizes': self._calculate_section_sizes(schedule),
            'term_summary': self._generate_term_summary(schedule)
        }
        return stats

    def _calculate_room_utilization(self, schedule, rooms):
        """Calculate room utilization statistics"""
        utilization = {}
        for room in rooms:
            room_stats = {'term1': 0, 'term2': 0}
            total_blocks = len(self.blocks)
            
            for term in ['term1', 'term2']:
                used_blocks = len([b for b in self.blocks 
                                 if b in schedule['room_schedules'][room][term]])
                room_stats[term] = (used_blocks / total_blocks) * 100
            
            utilization[room] = room_stats
        return utilization

    def _calculate_section_sizes(self, schedule):
        """Calculate section size distribution"""
        sizes = defaultdict(lambda: {'term1': [], 'term2': []})
        for course, terms in schedule['course_sections'].items():
            for term in ['term1', 'term2']:
                for section in terms[term]:
                    sizes[course][term].append(section['students'])
        return sizes

    def _generate_term_summary(self, schedule):
        """Generate term-wise scheduling summary"""
        summary = {
            'term1': {'total_sections': 0, 'total_students': 0},
            'term2': {'total_sections': 0, 'total_students': 0}
        }
        
        for course, terms in schedule['course_sections'].items():
            for term in ['term1', 'term2']:
                summary[term]['total_sections'] += len(terms[term])
                summary[term]['total_students'] += sum(s['students'] for s in terms[term])
        
        return summary

    def print_schedule(self, schedule, statistics):
        """Print the complete schedule with statistics"""
        print("\n=== SCHEDULE AND STATISTICS REPORT ===\n")
        
        # Print room utilization
        print("ROOM UTILIZATION:")
        print("-" * 60)
        for room, stats in statistics['room_utilization'].items():
            print(f"Room {room}:")
            print(f"  Term 1: {stats['term1']:.1f}% utilized")
            print(f"  Term 2: {stats['term2']:.1f}% utilized")
        
        # Print section size distribution
        print("\nSECTION SIZE DISTRIBUTION:")
        print("-" * 60)
        for course, terms in statistics['section_sizes'].items():
            print(f"\n{course} ({self.courses[course]['title']}):")
            for term in ['term1', 'term2']:
                if terms[term]:
                    avg_size = sum(terms[term]) / len(terms[term])
                    print(f"  Term {term[-1]}: {len(terms[term])} sections, "
                          f"avg size: {avg_size:.1f}")
        
        # Print term summary
        print("\nTERM SUMMARY:")
        print("-" * 60)
        for term, stats in statistics['term_summary'].items():
            print(f"\n{term.upper()}:")
            print(f"  Total sections: {stats['total_sections']}")
            print(f"  Total students enrolled: {stats['total_students']}")
            if stats['total_sections'] > 0:
                avg_size = stats['total_students'] / stats['total_sections']
                print(f"  Average section size: {avg_size:.1f}")

    def print_student_schedule(self, student_id, schedule):
        """Print a formatted schedule for a specific student"""
        if student_id not in schedule['student_schedules']:
            print(f"No schedule found for student {student_id}")
            return
        
        student_schedule = schedule['student_schedules'][student_id]
        print(f"\n=== Schedule for Student {student_id} ===\n")
        
        for term in ['term1', 'term2']:
            print(f"\n{term.upper()}")
            print("-" * 80)
            print(f"{'Block':<10} {'Course':<15} {'Title':<40} {'Section':<10}")
            print("-" * 80)
            
            for block in self.blocks:
                if block in student_schedule[term]:
                    course_info = student_schedule[term][block]
                    print(f"{block:<10} {course_info['course']:<15} {course_info['title']:<40} {course_info['section']:<10}")
                else:
                    print(f"{block:<10} {'---':<15} {'---':<40} {'---':<10}")

    def get_lecturer_schedule(self, lecturer_id, schedule):
        """Get a formatted schedule for a specific lecturer"""
        if lecturer_id not in self.lecturer_ids:
            return None
            
        lecturer_schedule = {
            'term1': {day: {block: None for block in self.daily_blocks} 
                     for day in self.days},
            'term2': {day: {block: None for block in self.daily_blocks} 
                     for day in self.days}
        }
        
        # Find all courses taught by this lecturer
        lecturer_courses = self.teacher_courses.get(lecturer_id, [])
        
        for term_num in [1, 2]:
            term = f'term{term_num}'
            for course in lecturer_courses:
                if course in schedule['course_sections']:
                    for section in schedule['course_sections'][course][term]:
                        block = section['block']
                        day, time = block.split('-')
                        lecturer_schedule[term][day][time] = {
                            'course': course,
                            'section': section['section'],
                            'room': section['room'],
                            'students': section['students'],
                            'title': self.courses[course]['title']
                        }
        
        return {
            'id': lecturer_id,
            'schedule': lecturer_schedule
        }

    def get_student_schedule(self, student_id, schedule):
        """Get a formatted schedule for a specific student"""
        if student_id not in schedule['student_schedules']:
            return None
            
        student_schedule = {
            'term1': {day: {block: None for block in self.daily_blocks} 
                     for day in self.days},
            'term2': {day: {block: None for block in self.daily_blocks} 
                     for day in self.days}
        }
        
        raw_schedule = schedule['student_schedules'][student_id]
        
        for term in ['term1', 'term2']:
            for block, course_info in raw_schedule[term].items():
                day, time = block.split('-')
                # Find lecturer for this course
                lecturer_id = next((lid for lid, courses in self.teacher_courses.items() 
                                  if course_info['course'] in courses), None)
                
                student_schedule[term][day][time] = {
                    'course': course_info['course'],
                    'title': course_info['title'],
                    'section': course_info['section'],
                    'lecturer': lecturer_id if lecturer_id else 'Unknown',
                    'room': next((sec['room'] 
                                for sec in schedule['course_sections'][course_info['course']][term] 
                                if sec['section'] == course_info['section'] 
                                and sec['block'] == block), 'Unknown')
                }
        
        return student_schedule

def main():
    try:
        # Load data
        lecturer_data = pd.read_excel('cleaned_dataset.xlsx', sheet_name='Lecturer Details')
        rooms_data = pd.read_excel('cleaned_dataset.xlsx', sheet_name='Rooms data')
        course_data = pd.read_excel('cleaned_dataset.xlsx', sheet_name='Course list')
        student_requests = pd.read_excel('cleaned_dataset.xlsx', sheet_name='Student requests')
        
        print("Data loaded successfully. Creating schedule...")
        
        # Create and run scheduler
        scheduler = CourseScheduler(lecturer_data, rooms_data, course_data, student_requests)
        schedule, statistics = scheduler.create_schedule()
        
        # Save schedule data for the Streamlit app
        with open('schedule.pkl', 'wb') as f:
            pickle.dump(schedule, f)
        
        # Print complete schedule with statistics
        scheduler.print_schedule(schedule, statistics)
        
        # Print example student schedule
        if len(student_requests['student_id']) > 0:
            example_student = student_requests['student_id'].iloc[0]
            print(f"\nExample Student Schedule (ID: {example_student}):")
            scheduler.print_student_schedule(example_student, schedule)
            
        print("\nSchedule has been saved. You can now run 'streamlit run app.py' to view the schedules.")
            
    except Exception as e:
        print(f"An error occurred: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()