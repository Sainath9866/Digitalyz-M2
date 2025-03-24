import streamlit as st
import pandas as pd
from main import CourseScheduler
import pickle

st.set_page_config(page_title="Course Schedule Viewer", layout="wide")

def load_schedule():
    try:
        with open('schedule.pkl', 'rb') as f:
            return pickle.load(f)
    except:
        return None

def format_schedule_table(schedule_data, term):
    """Convert schedule data to a pandas DataFrame for display"""
    if not schedule_data:
        return pd.DataFrame()
        
    data = []
    for block in ['Morning', 'Afternoon', 'Evening']:
        row = {'Time Block': block}
        for day in ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']:
            cell = schedule_data[term][day][block]
            if cell:
                text = f"{cell['course']} - {cell['title']}\n"
                text += f"Section: {cell['section']}\n"
                if 'lecturer' in cell:  # Student view
                    text += f"Lecturer: {cell['lecturer']}\n"
                if 'students' in cell:  # Lecturer view
                    text += f"Students: {cell['students']}\n"
                text += f"Room: {cell['room']}"
                row[day] = text
            else:
                row[day] = "---"
        data.append(row)
    
    return pd.DataFrame(data)

def main():
    st.title("Course Schedule Viewer")
    
    # Load data and scheduler
    try:
        lecturer_data = pd.read_excel('cleaned_dataset.xlsx', sheet_name='Lecturer Details')
        rooms_data = pd.read_excel('cleaned_dataset.xlsx', sheet_name='Rooms data')
        course_data = pd.read_excel('cleaned_dataset.xlsx', sheet_name='Course list')
        student_requests = pd.read_excel('cleaned_dataset.xlsx', sheet_name='Student requests')
        
        scheduler = CourseScheduler(lecturer_data, rooms_data, course_data, student_requests)
        schedule_data = load_schedule()
        
        if not schedule_data:
            st.error("No schedule data found. Please run main.py first to generate the schedule.")
            return
            
        # Sidebar for navigation
        view_option = st.sidebar.selectbox(
            "Select View",
            ["Room Schedules", "Course Sections", "Student Schedules"]
        )

        if view_option == "Room Schedules":
            st.header("Room Schedules")
            
            # Select term
            term = st.selectbox("Select Term", ["Term 1", "Term 2"])
            term_key = f"term{term[-1]}"
            
            # Get all rooms
            rooms = sorted(schedule_data['room_schedules'].keys())
            selected_room = st.selectbox("Select Room", rooms)
            
            if selected_room:
                st.subheader(f"Schedule for Room {selected_room} - {term}")
                
                # Create a DataFrame for the room schedule
                room_data = []
                room_schedule = schedule_data['room_schedules'][selected_room][term_key]
                
                for block in room_schedule:
                    for course_info in room_schedule[block]:
                        room_data.append({
                            'Block': block,
                            'Course': course_info['course'],
                            'Section': course_info['section'],
                            'Students': course_info['students']
                        })
                
                if room_data:
                    df = pd.DataFrame(room_data)
                    st.dataframe(df, use_container_width=True)
                else:
                    st.info("No classes scheduled in this room for the selected term.")

        elif view_option == "Course Sections":
            st.header("Course Sections")
            
            # Select term
            term = st.selectbox("Select Term", ["Term 1", "Term 2"])
            term_key = f"term{term[-1]}"
            
            # Get all courses
            courses = sorted(schedule_data['course_sections'].keys())
            selected_course = st.selectbox("Select Course", courses)
            
            if selected_course:
                st.subheader(f"Sections for {selected_course} - {term}")
                
                # Create a DataFrame for the course sections
                section_data = []
                course_schedule = schedule_data['course_sections'][selected_course][term_key]
                
                for section in course_schedule:
                    section_data.append({
                        'Section': section['section'],
                        'Block': section['block'],
                        'Room': section['room'],
                        'Students': section['students']
                    })
                
                if section_data:
                    df = pd.DataFrame(section_data)
                    st.dataframe(df, use_container_width=True)
                else:
                    st.info("No sections scheduled for this course in the selected term.")

        elif view_option == "Student Schedules":
            st.header("Student Schedules")
            
            # Get all students
            students = sorted(schedule_data['student_schedules'].keys())
            selected_student = st.selectbox("Select Student", students)
            
            if selected_student:
                # Select term
                term = st.selectbox("Select Term", ["Term 1", "Term 2"])
                term_key = f"term{term[-1]}"
                
                st.subheader(f"Schedule for Student {selected_student} - {term}")
                
                # Create a DataFrame for the student schedule
                student_data = []
                student_schedule = schedule_data['student_schedules'][selected_student][term_key]
                
                for block, course_info in student_schedule.items():
                    if course_info:  # Only add blocks where a course is scheduled
                        student_data.append({
                            'Block': block,
                            'Course': course_info['course'],
                            'Title': course_info['title'],
                            'Section': course_info['section']
                        })
                
                if student_data:
                    df = pd.DataFrame(student_data)
                    st.dataframe(df, use_container_width=True)
                else:
                    st.info("No courses scheduled for this student in the selected term.")

    except Exception as e:
        st.error(f"An error occurred: {str(e)}")
        st.error("Please make sure the schedule.pkl file exists and is valid.")

if __name__ == "__main__":
    main() 