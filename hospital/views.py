from django.shortcuts import render,redirect,reverse
from . import forms,models
from django.db.models import Sum
from django.contrib.auth.models import Group
from django.http import HttpResponseRedirect
from django.core.mail import send_mail
from django.contrib.auth.decorators import login_required,user_passes_test
from datetime import datetime,timedelta,date
from django.conf import settings
from .models import Patient, PatientPrediction
import json
import pickle
import pandas as pd
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from .models import Appointment, Patient, Doctor
from .forms import PrescriptionForm

from fuzzywuzzy import process
from difflib import get_close_matches
from nltk.tokenize import word_tokenize

# Adding new code in doctor related views
import datetime
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.messages import get_messages  # To clear old messages if needed
from . import models, forms

# New code for other functions
import re
import json
import nltk
from django.http import JsonResponse
from nltk.tokenize import word_tokenize

nltk.download("punkt")
nltk.download("punkt_tab")



MODEL_PATH = "model/finalized_model.sav"
FEATURES_PATH = "model/features.pkl"

with open(FEATURES_PATH, 'rb') as f:
    feature_names = pickle.load(f)

loaded_model = pickle.load(open(MODEL_PATH, 'rb'))

def predict_disease(symptoms_list):
    """
    Predict disease based on symptoms using the trained ML model.
    """
    input_df = pd.DataFrame(columns=feature_names, index=[0])
    input_df = input_df.fillna(0)  # Initialize all features to zero

    for symptom in symptoms_list:
        for col in input_df.columns:
            if symptom in col.lower():  # Case-insensitive matching
                input_df.loc[0, col] = 1
                break

    prediction = loaded_model.predict(input_df)
    return prediction[0]  # Return predicted disease


# Create your views here.
def home_view(request):
    if request.user.is_authenticated:
        return HttpResponseRedirect('afterlogin')
    return render(request,'hospital/index.html')


#for showing signup/login button for admin(by sumit)
def adminclick_view(request):
    if request.user.is_authenticated:
        return HttpResponseRedirect('afterlogin')
    return render(request,'hospital/adminclick.html')


#for showing signup/login button for doctor(by sumit)
def doctorclick_view(request):
    if request.user.is_authenticated:
        return HttpResponseRedirect('afterlogin')
    return render(request,'hospital/doctorclick.html')


#for showing signup/login button for patient(by sumit)
def patientclick_view(request):
    if request.user.is_authenticated:
        return HttpResponseRedirect('afterlogin')
    return render(request,'hospital/patientclick.html')




def admin_signup_view(request):
    form=forms.AdminSigupForm()
    if request.method=='POST':
        form=forms.AdminSigupForm(request.POST)
        if form.is_valid():
            user=form.save()
            user.set_password(user.password)
            user.save()
            my_admin_group = Group.objects.get_or_create(name='ADMIN')
            my_admin_group[0].user_set.add(user)
            return HttpResponseRedirect('adminlogin')
    return render(request,'hospital/adminsignup.html',{'form':form})




def doctor_signup_view(request):
    userForm=forms.DoctorUserForm()
    doctorForm=forms.DoctorForm()
    mydict={'userForm':userForm,'doctorForm':doctorForm}
    if request.method=='POST':
        userForm=forms.DoctorUserForm(request.POST)
        doctorForm=forms.DoctorForm(request.POST,request.FILES)
        if userForm.is_valid() and doctorForm.is_valid():
            user=userForm.save()
            user.set_password(user.password)
            user.save()
            doctor=doctorForm.save(commit=False)
            doctor.user=user
            doctor=doctor.save()
            my_doctor_group = Group.objects.get_or_create(name='DOCTOR')
            my_doctor_group[0].user_set.add(user)
        return HttpResponseRedirect('doctorlogin')
    return render(request,'hospital/doctorsignup.html',context=mydict)


def patient_signup_view(request):
    userForm = forms.PatientUserForm()
    patientForm = forms.PatientForm()
    mydict = {'userForm': userForm, 'patientForm': patientForm}

    if request.method == 'POST':
        userForm = forms.PatientUserForm(request.POST)
        patientForm = forms.PatientForm(request.POST, request.FILES)

        if userForm.is_valid() and patientForm.is_valid():
            user = userForm.save(commit=False)
            user.set_password(user.password)
            user.save()

            patient = patientForm.save(commit=False)
            patient.user = user
            patient.save()

            # Assign user to 'PATIENT' group
            my_patient_group, _ = Group.objects.get_or_create(name='PATIENT')
            my_patient_group.user_set.add(user)

            return HttpResponseRedirect('patientlogin')  # Redirect after successful registration

    return render(request, 'hospital/patientsignup.html', context=mydict)


#-----------for checking user is doctor , patient or admin
def is_admin(user):
    return user.groups.filter(name='ADMIN').exists()
def is_doctor(user):
    return user.groups.filter(name='DOCTOR').exists()
def is_patient(user):
    return user.groups.filter(name='PATIENT').exists()


#---------AFTER ENTERING CREDENTIALS WE CHECK WHETHER USERNAME AND PASSWORD IS OF ADMIN,DOCTOR OR PATIENT
def afterlogin_view(request):
    if is_admin(request.user):
        return redirect('admin-dashboard')
    elif is_doctor(request.user):
        accountapproval=models.Doctor.objects.all().filter(user_id=request.user.id,status=True)
        if accountapproval:
            return redirect('doctor-dashboard')
        else:
            return render(request,'hospital/doctor_wait_for_approval.html')
    elif is_patient(request.user):
        accountapproval=models.Patient.objects.all().filter(user_id=request.user.id,status=True)
        if accountapproval:
            return redirect('patient-dashboard')
        else:
            return render(request,'hospital/patient_wait_for_approval.html')

    




#---------------------------------------------------------------------------------
#------------------------ ADMIN RELATED VIEWS START ------------------------------
#---------------------------------------------------------------------------------
@login_required(login_url='adminlogin')
@user_passes_test(is_admin)
def admin_dashboard_view(request):
    #for both table in admin dashboard
    doctors=models.Doctor.objects.all().order_by('-id')
    patients=models.Patient.objects.all().order_by('-id')
    #for three cards
    doctorcount=models.Doctor.objects.all().filter(status=True).count()
    pendingdoctorcount=models.Doctor.objects.all().filter(status=False).count()

    patientcount=models.Patient.objects.all().filter(status=True).count()
    pendingpatientcount=models.Patient.objects.all().filter(status=False).count()

    appointmentcount=models.Appointment.objects.all().filter(status=True).count()
    pendingappointmentcount=models.Appointment.objects.all().filter(status=False).count()
    mydict={
    'doctors':doctors,
    'patients':patients,
    'doctorcount':doctorcount,
    'pendingdoctorcount':pendingdoctorcount,
    'patientcount':patientcount,
    'pendingpatientcount':pendingpatientcount,
    'appointmentcount':appointmentcount,
    'pendingappointmentcount':pendingappointmentcount,
    }
    return render(request,'hospital/admin_dashboard.html',context=mydict)


# this view for sidebar click on admin page
@login_required(login_url='adminlogin')
@user_passes_test(is_admin)
def admin_doctor_view(request):
    return render(request,'hospital/admin_doctor.html')



@login_required(login_url='adminlogin')
@user_passes_test(is_admin)
def admin_view_doctor_view(request):
    doctors=models.Doctor.objects.all().filter(status=True)
    return render(request,'hospital/admin_view_doctor.html',{'doctors':doctors})



@login_required(login_url='adminlogin')
@user_passes_test(is_admin)
def delete_doctor_from_hospital_view(request,pk):
    doctor=models.Doctor.objects.get(id=pk)
    user=models.User.objects.get(id=doctor.user_id)
    user.delete()
    doctor.delete()
    return redirect('admin-view-doctor')



@login_required(login_url='adminlogin')
@user_passes_test(is_admin)
def update_doctor_view(request,pk):
    doctor=models.Doctor.objects.get(id=pk)
    user=models.User.objects.get(id=doctor.user_id)

    userForm=forms.DoctorUserForm(instance=user)
    doctorForm=forms.DoctorForm(request.FILES,instance=doctor)
    mydict={'userForm':userForm,'doctorForm':doctorForm}
    if request.method=='POST':
        userForm=forms.DoctorUserForm(request.POST,instance=user)
        doctorForm=forms.DoctorForm(request.POST,request.FILES,instance=doctor)
        if userForm.is_valid() and doctorForm.is_valid():
            user=userForm.save()
            user.set_password(user.password)
            user.save()
            doctor=doctorForm.save(commit=False)
            doctor.status=True
            doctor.save()
            return redirect('admin-view-doctor')
    return render(request,'hospital/admin_update_doctor.html',context=mydict)




@login_required(login_url='adminlogin')
@user_passes_test(is_admin)
def admin_add_doctor_view(request):
    userForm=forms.DoctorUserForm()
    doctorForm=forms.DoctorForm()
    mydict={'userForm':userForm,'doctorForm':doctorForm}
    if request.method=='POST':
        userForm=forms.DoctorUserForm(request.POST)
        doctorForm=forms.DoctorForm(request.POST, request.FILES)
        if userForm.is_valid() and doctorForm.is_valid():
            user=userForm.save()
            user.set_password(user.password)
            user.save()

            doctor=doctorForm.save(commit=False)
            doctor.user=user
            doctor.status=True
            doctor.save()

            my_doctor_group = Group.objects.get_or_create(name='DOCTOR')
            my_doctor_group[0].user_set.add(user)

        return HttpResponseRedirect('admin-view-doctor')
    return render(request,'hospital/admin_add_doctor.html',context=mydict)




@login_required(login_url='adminlogin')
@user_passes_test(is_admin)
def admin_approve_doctor_view(request):
    #those whose approval are needed
    doctors=models.Doctor.objects.all().filter(status=False)
    return render(request,'hospital/admin_approve_doctor.html',{'doctors':doctors})


@login_required(login_url='adminlogin')
@user_passes_test(is_admin)
def approve_doctor_view(request,pk):
    doctor=models.Doctor.objects.get(id=pk)
    doctor.status=True
    doctor.save()
    return redirect(reverse('admin-approve-doctor'))


@login_required(login_url='adminlogin')
@user_passes_test(is_admin)
def reject_doctor_view(request,pk):
    doctor=models.Doctor.objects.get(id=pk)
    user=models.User.objects.get(id=doctor.user_id)
    user.delete()
    doctor.delete()
    return redirect('admin-approve-doctor')



@login_required(login_url='adminlogin')
@user_passes_test(is_admin)
def admin_view_doctor_specialisation_view(request):
    doctors=models.Doctor.objects.all().filter(status=True)
    return render(request,'hospital/admin_view_doctor_specialisation.html',{'doctors':doctors})



@login_required(login_url='adminlogin')
@user_passes_test(is_admin)
def admin_patient_view(request):
    return render(request,'hospital/admin_patient.html')



@login_required(login_url='adminlogin')
@user_passes_test(is_admin)
def admin_view_patient_view(request):
    patients=models.Patient.objects.all().filter(status=True)
    return render(request,'hospital/admin_view_patient.html',{'patients':patients})



@login_required(login_url='adminlogin')
@user_passes_test(is_admin)
def delete_patient_from_hospital_view(request,pk):
    patient=models.Patient.objects.get(id=pk)
    user=models.User.objects.get(id=patient.user_id)
    user.delete()
    patient.delete()
    return redirect('admin-view-patient')



@login_required(login_url='adminlogin')
@user_passes_test(is_admin)
def update_patient_view(request,pk):
    patient=models.Patient.objects.get(id=pk)
    user=models.User.objects.get(id=patient.user_id)

    userForm=forms.PatientUserForm(instance=user)
    patientForm=forms.PatientForm(request.FILES,instance=patient)
    mydict={'userForm':userForm,'patientForm':patientForm}
    if request.method=='POST':
        userForm=forms.PatientUserForm(request.POST,instance=user)
        patientForm=forms.PatientForm(request.POST,request.FILES,instance=patient)
        if userForm.is_valid() and patientForm.is_valid():
            user=userForm.save()
            user.set_password(user.password)
            user.save()
            patient=patientForm.save(commit=False)
            patient.status=True
            patient.assignedDoctorId=request.POST.get('assignedDoctorId')
            patient.save()
            return redirect('admin-view-patient')
    return render(request,'hospital/admin_update_patient.html',context=mydict)





@login_required(login_url='adminlogin')
@user_passes_test(is_admin)
def admin_add_patient_view(request):
    userForm=forms.PatientUserForm()
    patientForm=forms.PatientForm()
    mydict={'userForm':userForm,'patientForm':patientForm}
    if request.method=='POST':
        userForm=forms.PatientUserForm(request.POST)
        patientForm=forms.PatientForm(request.POST,request.FILES)
        if userForm.is_valid() and patientForm.is_valid():
            user=userForm.save()
            user.set_password(user.password)
            user.save()

            patient=patientForm.save(commit=False)
            patient.user=user
            patient.status=True
            patient.assignedDoctorId=request.POST.get('assignedDoctorId')
            patient.save()

            my_patient_group = Group.objects.get_or_create(name='PATIENT')
            my_patient_group[0].user_set.add(user)

        return HttpResponseRedirect('admin-view-patient')
    return render(request,'hospital/admin_add_patient.html',context=mydict)


#------------------FOR APPROVING PATIENT BY ADMIN----------------------
@login_required(login_url='adminlogin')
@user_passes_test(is_admin)
def admin_approve_patient_view(request):
    #those whose approval are needed
    patients=models.Patient.objects.all().filter(status=False)
    return render(request,'hospital/admin_approve_patient.html',{'patients':patients})



@login_required(login_url='adminlogin')
@user_passes_test(is_admin)
def approve_patient_view(request,pk):
    patient=models.Patient.objects.get(id=pk)
    patient.status=True
    patient.save()
    return redirect(reverse('admin-approve-patient'))



@login_required(login_url='adminlogin')
@user_passes_test(is_admin)
def reject_patient_view(request,pk):
    patient=models.Patient.objects.get(id=pk)
    user=models.User.objects.get(id=patient.user_id)
    user.delete()
    patient.delete()
    return redirect('admin-approve-patient')



#--------------------- FOR DISCHARGING PATIENT BY ADMIN START-------------------------
@login_required(login_url='adminlogin')
@user_passes_test(is_admin)
def admin_discharge_patient_view(request):
    patients=models.Patient.objects.all().filter(status=True)
    return render(request,'hospital/admin_discharge_patient.html',{'patients':patients})



@login_required(login_url='adminlogin')
@user_passes_test(is_admin)
def discharge_patient_view(request,pk):
    patient=models.Patient.objects.get(id=pk)
    days=(date.today()-patient.admitDate) #2 days, 0:00:00
    assignedDoctor=models.User.objects.all().filter(id=patient.assignedDoctorId)
    d=days.days # only how many day that is 2
    patientDict={
        'patientId':pk,
        'name':patient.get_name,
        'mobile':patient.mobile,
        'address':patient.address,
        'symptoms':patient.symptoms,
        'admitDate':patient.admitDate,
        'todayDate':date.today(),
        'day':d,
        'assignedDoctorName':assignedDoctor[0].first_name,
    }
    if request.method == 'POST':
        feeDict ={
            'roomCharge':int(request.POST['roomCharge'])*int(d),
            'doctorFee':request.POST['doctorFee'],
            'medicineCost' : request.POST['medicineCost'],
            'OtherCharge' : request.POST['OtherCharge'],
            'total':(int(request.POST['roomCharge'])*int(d))+int(request.POST['doctorFee'])+int(request.POST['medicineCost'])+int(request.POST['OtherCharge'])
        }
        patientDict.update(feeDict)
        #for updating to database patientDischargeDetails (pDD)
        pDD=models.PatientDischargeDetails()
        pDD.patientId=pk
        pDD.patientName=patient.get_name
        pDD.assignedDoctorName=assignedDoctor[0].first_name
        pDD.address=patient.address
        pDD.mobile=patient.mobile
        pDD.symptoms=patient.symptoms
        pDD.admitDate=patient.admitDate
        pDD.releaseDate=date.today()
        pDD.daySpent=int(d)
        pDD.medicineCost=int(request.POST['medicineCost'])
        pDD.roomCharge=int(request.POST['roomCharge'])*int(d)
        pDD.doctorFee=int(request.POST['doctorFee'])
        pDD.OtherCharge=int(request.POST['OtherCharge'])
        pDD.total=(int(request.POST['roomCharge'])*int(d))+int(request.POST['doctorFee'])+int(request.POST['medicineCost'])+int(request.POST['OtherCharge'])
        pDD.save()
        return render(request,'hospital/patient_final_bill.html',context=patientDict)
    return render(request,'hospital/patient_generate_bill.html',context=patientDict)



#--------------for discharge patient bill (pdf) download and printing
import io
from xhtml2pdf import pisa
from django.template.loader import get_template
from django.template import Context
from django.http import HttpResponse


def render_to_pdf(template_src, context_dict):
    template = get_template(template_src)
    html  = template.render(context_dict)
    result = io.BytesIO()
    pdf = pisa.pisaDocument(io.BytesIO(html.encode("ISO-8859-1")), result)
    if not pdf.err:
        return HttpResponse(result.getvalue(), content_type='application/pdf')
    return



def download_pdf_view(request,pk):
    dischargeDetails=models.PatientDischargeDetails.objects.all().filter(patientId=pk).order_by('-id')[:1]
    dict={
        'patientName':dischargeDetails[0].patientName,
        'assignedDoctorName':dischargeDetails[0].assignedDoctorName,
        'address':dischargeDetails[0].address,
        'mobile':dischargeDetails[0].mobile,
        'symptoms':dischargeDetails[0].symptoms,
        'admitDate':dischargeDetails[0].admitDate,
        'releaseDate':dischargeDetails[0].releaseDate,
        'daySpent':dischargeDetails[0].daySpent,
        'medicineCost':dischargeDetails[0].medicineCost,
        'roomCharge':dischargeDetails[0].roomCharge,
        'doctorFee':dischargeDetails[0].doctorFee,
        'OtherCharge':dischargeDetails[0].OtherCharge,
        'total':dischargeDetails[0].total,
    }
    return render_to_pdf('hospital/download_bill.html',dict)



#-----------------APPOINTMENT START--------------------------------------------------------------------
@login_required(login_url='adminlogin')
@user_passes_test(is_admin)
def admin_appointment_view(request):
    return render(request,'hospital/admin_appointment.html')



@login_required(login_url='adminlogin')
@user_passes_test(is_admin)
def admin_view_appointment_view(request):
    appointments=models.Appointment.objects.all().filter(status=True)
    return render(request,'hospital/admin_view_appointment.html',{'appointments':appointments})



@login_required(login_url='adminlogin')
@user_passes_test(is_admin)
def admin_add_appointment_view(request):
    appointmentForm=forms.AppointmentForm()
    mydict={'appointmentForm':appointmentForm,}
    if request.method=='POST':
        appointmentForm=forms.AppointmentForm(request.POST)
        if appointmentForm.is_valid():
            appointment=appointmentForm.save(commit=False)
            appointment.doctorId=request.POST.get('doctorId')
            appointment.patientId=request.POST.get('patientId')
            appointment.doctorName=models.User.objects.get(id=request.POST.get('doctorId')).first_name
            appointment.patientName=models.User.objects.get(id=request.POST.get('patientId')).first_name
            appointment.status=True
            appointment.save()
        return HttpResponseRedirect('admin-view-appointment')
    return render(request,'hospital/admin_add_appointment.html',context=mydict)



@login_required(login_url='adminlogin')
@user_passes_test(is_admin)
def admin_approve_appointment_view(request):
    #those whose approval are needed
    appointments=models.Appointment.objects.all().filter(status=False)
    return render(request,'hospital/admin_approve_appointment.html',{'appointments':appointments})



@login_required(login_url='adminlogin')
@user_passes_test(is_admin)
def approve_appointment_view(request,pk):
    appointment=models.Appointment.objects.get(id=pk)
    appointment.status=True
    appointment.save()
    return redirect(reverse('admin-approve-appointment'))



@login_required(login_url='adminlogin')
@user_passes_test(is_admin)
def reject_appointment_view(request,pk):
    appointment=models.Appointment.objects.get(id=pk)
    appointment.delete()
    return redirect('admin-approve-appointment')



#--------------------- FOR Approving/Rejecting the Leave BY ADMIN START------------
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from hospital.models import DoctorLeave

@login_required
def admin_view_doctor_leave_requests(request):
    """View all doctor leave requests."""
    leave_requests = DoctorLeave.objects.all()
    return render(request, 'hospital/admin_view_doctor_leave_requests.html', {'leave_requests': leave_requests})

@login_required
def approve_leave(request, leave_id):
    """Approve a doctor's leave request."""
    leave_request = get_object_or_404(DoctorLeave, id=leave_id)
    leave_request.status = "Approved"
    leave_request.save()
    return redirect('admin-view-doctor-leave-requests')

@login_required
def reject_leave(request, leave_id):
    """Reject a doctor's leave request."""
    leave_request = get_object_or_404(DoctorLeave, id=leave_id)
    leave_request.status = "Rejected"
    leave_request.save()
    return redirect('admin-view-doctor-leave-requests')

#--------------------- FOR Approving/Rejecting the Leave BY ADMIN END-----------------


#---------------------------------------------------------------------------------
#------------------------ ADMIN RELATED VIEWS END ------------------------------
#---------------------------------------------------------------------------------






#-------------------------------------
# --------------------------------------------
#------------------------ DOCTOR RELATED VIEWS START ------------------------------
#---------------------------------------------------------------------------------
@login_required(login_url='doctorlogin')
@user_passes_test(is_doctor)
def doctor_dashboard_view(request):
    #for three cards
    # patientcount=models.Patient.objects.all().filter(status=True,assignedDoctorId=request.user.id).count()
    patientcount=models.Patient.objects.all().filter(status=True).count()
    appointmentcount=models.Appointment.objects.all().filter(status=True,doctorId=request.user.id).count()
    patientdischarged=models.PatientDischargeDetails.objects.all().distinct().filter(assignedDoctorName=request.user.first_name).count()

    #for  table in doctor dashboard
    appointments=models.Appointment.objects.all().filter(status=True,doctorId=request.user.id).order_by('-id')
    patientid=[]
    for a in appointments:
        patientid.append(a.patientId)
    patients=models.Patient.objects.all().filter(status=True,user_id__in=patientid).order_by('-id')
    appointments=zip(appointments,patients)
    mydict={
    'patientcount':patientcount,
    'appointmentcount':appointmentcount,
    'patientdischarged':patientdischarged,
    'appointments':appointments,
    'doctor':models.Doctor.objects.get(user_id=request.user.id), #for profile picture of doctor in sidebar
    }
    return render(request,'hospital/doctor_dashboard.html',context=mydict)



@login_required(login_url='doctorlogin')
@user_passes_test(is_doctor)
def doctor_patient_view(request):
    mydict={
    'doctor':models.Doctor.objects.get(user_id=request.user.id), #for profile picture of doctor in sidebar
    }
    return render(request,'hospital/doctor_patient.html',context=mydict)



@login_required(login_url='doctorlogin')
@user_passes_test(is_doctor)
def doctor_view_patient_view(request):
    doctor = models.Doctor.objects.get(user_id=request.user.id)

    # Get all patients who have appointments with the logged-in doctor
    patient_ids = models.Appointment.objects.filter(doctorId=request.user.id).values_list('patientId', flat=True)
    patients = models.Patient.objects.filter(user_id__in=patient_ids, status=True)

    return render(request, 'hospital/doctor_view_patient.html', {'patients': patients, 'doctor': doctor})


@login_required(login_url='doctorlogin')
@user_passes_test(is_doctor)
def doctor_view_discharge_patient_view(request):
    dischargedpatients=models.PatientDischargeDetails.objects.all().distinct().filter(assignedDoctorName=request.user.first_name)
    doctor=models.Doctor.objects.get(user_id=request.user.id) #for profile picture of doctor in sidebar
    return render(request,'hospital/doctor_view_discharge_patient.html',{'dischargedpatients':dischargedpatients,'doctor':doctor})



@login_required(login_url='doctorlogin')
@user_passes_test(is_doctor)
def doctor_appointment_view(request):
    doctor=models.Doctor.objects.get(user_id=request.user.id) #for profile picture of doctor in sidebar
    return render(request,'hospital/doctor_appointment.html',{'doctor':doctor})



# @login_required(login_url='doctorlogin')
# def doctor_view_appointment_view(request):
#     doctor = models.Doctor.objects.get(user_id=request.user.id)
#     appointments = models.Appointment.objects.all().filter(status= True, doctorId=request.user.id)
#     patientid = []
#     for a in appointments:
#         patientid.append(a.patientId)
#     patients = models.Patient.objects.all().filter(status=True, user_id__in = patientid)
#     appointments = zip(appointments,patients)
#     return render(request, 'hospital/doctor_view_appointment.html',{'appointments':appointments,'doctor':doctor})

@login_required(login_url='doctorlogin')
def doctor_view_appointment_view(request):
    doctor = models.Doctor.objects.get(user_id=request.user.id)
    
    # Fetch all confirmed appointments for this doctor
    appointments = models.Appointment.objects.filter(status=True, doctorId=request.user.id)

    # Fetch patient details
    patient_ids = [a.patientId for a in appointments]
    patients = models.Patient.objects.filter(status=True, user_id__in=patient_ids)

    # Create a mapping for predictions (Latest prediction per patient)
    patient_predictions = {p.user_id: models.PatientPrediction.objects.filter(patient=p).order_by('-prediction_date').first() for p in patients}

    # Prepare data for rendering
    appointment_data = []
    for appointment, patient in zip(appointments, patients):
        predicted_disease = patient_predictions.get(patient.user_id, None)
        appointment_data.append({
            'appointment': appointment,
            'patient': patient,
            'predicted_disease': predicted_disease.predicted_disease if predicted_disease else "Not Available"
        })

    return render(request, 'hospital/doctor_view_appointment.html', {'appointments': appointment_data, 'doctor': doctor})


@login_required(login_url='doctorlogin')
@user_passes_test(is_doctor)
def doctor_delete_appointment_view(request):
    doctor=models.Doctor.objects.get(user_id=request.user.id) #for profile picture of doctor in sidebar
    appointments=models.Appointment.objects.all().filter(status=True,doctorId=request.user.id)
    patientid=[]
    for a in appointments:
        patientid.append(a.patientId)
    patients=models.Patient.objects.all().filter(status=True,user_id__in=patientid)
    appointments=zip(appointments,patients)
    return render(request,'hospital/doctor_delete_appointment.html',{'appointments':appointments,'doctor':doctor})



@login_required(login_url='doctorlogin')
@user_passes_test(is_doctor)
def delete_appointment_view(request,pk):
    appointment=models.Appointment.objects.get(id=pk)
    appointment.delete()
    doctor=models.Doctor.objects.get(user_id=request.user.id) #for profile picture of doctor in sidebar
    appointments=models.Appointment.objects.all().filter(status=True,doctorId=request.user.id)
    patientid=[]
    for a in appointments:
        patientid.append(a.patientId)
    patients=models.Patient.objects.all().filter(status=True,user_id__in=patientid)
    appointments=zip(appointments,patients)
    return render(request,'hospital/doctor_delete_appointment.html',{'appointments':appointments,'doctor':doctor})

#  for adding Prescription for the patient



def is_doctor(user):
    return user.groups.filter(name='DOCTOR').exists()

@login_required(login_url='doctorlogin')
@user_passes_test(is_doctor)
def prescribe_medicine(request, appointment_id):
    try:
        # Get the appointment instance
        appointment = get_object_or_404(Appointment, id=appointment_id)

        # Fetch patient and doctor using user_id
        patient = get_object_or_404(Patient, user_id=appointment.patientId)
        doctor = get_object_or_404(Doctor, user_id=appointment.doctorId)

        if request.method == 'POST':
            form = PrescriptionForm(request.POST)
            if form.is_valid():
                prescription = form.save(commit=False)
                prescription.patient = patient
                prescription.doctor = doctor
                prescription.appointment = appointment
                prescription.save()
                
                messages.success(request, "Prescription Added Successfully!")  
                return redirect('doctor-view-appointment')  # ✅ Correct redirect name
            else:
                messages.error(request, "Error adding prescription. Please check the form.")

        else:
            form = PrescriptionForm()

        return render(request, 'hospital/doctor_prescribe_medicine.html', {  # ✅ Updated template name
            'form': form,
            'patient': patient,
            'appointment': appointment
        })

    except Exception as e:
        messages.error(request, f"Unexpected error: {str(e)}")  
        return redirect('doctor-view-appointment')
    
    


@login_required(login_url='doctorlogin')
@user_passes_test(is_doctor)
def doctor_set_availability_view(request):
    doctor = models.Doctor.objects.get(user_id=request.user.id)
    
    # Clear any lingering messages from previous pages
    list(get_messages(request))

    selected_date = None
    if request.method == "GET":
        if 'date' in request.GET:
            try:
                selected_date = datetime.datetime.strptime(request.GET.get('date'), "%Y-%m-%d").date()
                if selected_date <= datetime.date.today():
                    messages.error(request, "Please select a future date (at least tomorrow).")
                    selected_date = None  # Do not load any time slots
            except Exception:
                messages.error(request, "Invalid date format.")
                selected_date = None
        form = forms.DoctorAvailabilityMultiForm(doctor=doctor, selected_date=selected_date)
    else:  # POST request
        try:
            selected_date = datetime.datetime.strptime(request.POST.get('date'), "%Y-%m-%d").date()
        except Exception:
            messages.error(request, "Invalid date format.")
            return redirect("doctor_set_availability")
        form = forms.DoctorAvailabilityMultiForm(request.POST, doctor=doctor, selected_date=selected_date)
        if form.is_valid():
            # Double-check for approved leave
            leave_exists = models.DoctorLeave.objects.filter(
                doctor=doctor,
                status="Approved",
                leave_start__lte=selected_date,
                leave_end__gte=selected_date
            ).exists()
            if leave_exists:
                messages.error(request, "You have approved leave on this date. Availability cannot be set.")
                return redirect("doctor_set_availability")
            time_slots = form.cleaned_data.get('time_slots')
            if not time_slots:
                messages.error(request, "No available time slots on this date. Please select a different date.")
                return redirect("doctor_set_availability")
            for slot in time_slots:
                start_time = datetime.datetime.strptime(slot, "%H:%M").time()
                dt = datetime.datetime.combine(selected_date, start_time)
                end_time = (dt + datetime.timedelta(hours=1)).time()
                models.DoctorAvailability.objects.create(
                    doctor=doctor,
                    date=selected_date,
                    start_time=start_time,
                    end_time=end_time
                )
            messages.success(request, "Availability set successfully!")
            return redirect("doctor_set_availability")
    context = {"form": form, "doctor": doctor}
    return render(request, "hospital/doctor_set_availability.html", context)


# Doctor leave
@login_required(login_url='doctorlogin')
@user_passes_test(is_doctor)
def doctor_apply_leave_view(request):
    doctor = models.Doctor.objects.get(user_id=request.user.id)
    if request.method == "POST":
        form = forms.DoctorLeaveForm(request.POST)
        if form.is_valid():
            leave = form.save(commit=False)
            leave.doctor = doctor
            leave.save()
            messages.success(request, "Leave applied successfully! Please wait for admin approval.")
            return redirect("doctor_apply_leave")
    else:
        form = forms.DoctorLeaveForm()
    context = {"form": form, "doctor": doctor}
    return render(request, "hospital/doctor_apply_leave.html", context)




#---------------------------------------------------------------------------------
#------------------------ DOCTOR RELATED VIEWS END ------------------------------
#---------------------------------------------------------------------------------






#---------------------------------------------------------------------------------
#------------------------ PATIENT RELATED VIEWS START ------------------------------
#---------------------------------------------------------------------------------



@login_required(login_url='patientlogin')
@user_passes_test(is_patient)
def patient_dashboard_view(request):
    patient=models.Patient.objects.get(user_id=request.user.id)
    # doctor=models.Doctor.objects.get(user_id=patient.assignedDoctorId)
    # doctor = patient.doctor if patient.doctor else None
    # newly Added code
    latest_appointment = models.Appointment.objects.filter(patientId=patient.user_id).order_by('-id').first()
    
    if latest_appointment:
        doctor = models.Doctor.objects.get(user_id=latest_appointment.doctorId)
    else:
        doctor = None  # No doctor assigned yet
    # old code
    mydict={
        'patient': patient,
        'doctorName': doctor.get_name if doctor else "Not Assigned",
        'doctorMobile': doctor.mobile if doctor else "N/A",
        'doctorAddress': doctor.address if doctor else "N/A",
        'doctorDepartment': doctor.department if doctor else "N/A",
        'admitDate': patient.admitDate,
        'symptoms': latest_appointment.symptoms if latest_appointment else "No symptoms recorded",
    }
    return render(request,'hospital/patient_dashboard.html',context=mydict)





@login_required(login_url='patientlogin')
@user_passes_test(is_patient)
def patient_appointment_view(request):
    patient=models.Patient.objects.get(user_id=request.user.id) #for profile picture of patient in sidebar
    return render(request,'hospital/patient_appointment.html',{'patient':patient})


# ###############################################with NLTK

import re
import json
from django.http import JsonResponse
from nltk.tokenize import word_tokenize
import nltk

SYMPTOMS_LIST = [
    "trouble_speaking", "understanding_others_words", "numbness", "arm_or_leg_unable_to_rise", "weak_vision",
    "headache", "trouble_in_walking", "seizure", "temporary_confusion", "staring_spell", "stiff_muscles",
    "uncontrollable_jerking_movements_of_the_arms_and_legs", "loss_of_consciousness", "fear", "anxiety",
    "radiating_chest_pain", "fatigue", "sweatings", "shortness_of_breath", "headache", "edema",
    "irregular_heartbeat", "dizziness", "palpitations", "fainting", "chest_pain", "cough", "pedel_edema",
    "lack_of_appetite", "nausea", "swelling_of_belly_area", "weight_gain", "high_blood_pressure",
    "headaches", "palpitations", "nose_bleeds", "shortness_of_breath_during_physical_activities",
    "wheezing", "chest_tightness", "change_in_sputum_color", "frequent_respiratory_infections",
    "lack_of_energy", "unintended_weight_loss", "cyanosis_of_lips", "rapid_heartbeat",
    "trouble_concentrating", "fever", "chest_pain_while_breathing", "cough_with_phlegm",
    "shaking_chills", "sweating", "body_temperature_lower_than_normal", "vomitings", "diarrhoea",
    "sore_throat", "muscle_or_body_aches", "loss_of_taste_or_smell", "trouble_staying_awake",
    "dry_cough", "extreme_tiredness", "muscles_and_joint_pain", "clubbing_of_nails",
    "heartburn", "backwash_of_food_or_sour_liquid_in_the_throat", "jaw_pain", "upper_belly_pain",
    "arm_pain", "dysphagia", "sensation_of_a_lump_in_the_throat", "ongoing_cough", "laryngitis",
    "burning_stomach_pain", "feeling_of_fullness", "bloating", "belching", "intolerance_to_fatty_foods",
    "blood_vomitings", "dark_blood_in_stools", "trouble_breathing", "feeling_faint",
    "appetite_changes", "hiccups", "dark_blood_in_stools_and_vomiting", "low-grade_fever",
    "burning_in_stomach", "sudden_nausea", "abdominal_pain_especially_in_the_upper_right_side",
    "clay_or_gray_colored_stool", "dark_urine", "joint_pain", "jaundice", "intense_itching",
    "easily_bleeding", "ascites", "spiderlike_blood_vessels_on_the_skin",
    "redness_in_the_palms_of_the_hands", "gynecomastia_in_men", "pale_fingernails",
    "clubbing_of_the_fingers", "confusion", "absence_of_periods_in_women",
    "drowsiness", "slurred_speech", "cognitive_issues", "portal_hypertension",
    "bleeding_or_bruising_easily", "shaking", "sweating", "hunger",
    "difficulty_concentrating", "numbness_of_lips", "difficulty_in_speaking",
    "loss_of_coordination", "blurry_vision", "high_blood_glucose_levels",
    "frequent_urination", "increased_thirst", "blurred_vision", "feeling_weak",
    "fruity-smelling_breath", "dry_mouth", "sudden_belly_pain",
    "pain_in_the_upper_belly_that_radiates_to_the_back", "pain_or_tenderness_in_the_abdomen",
    "rapid_pulse", "upset_stomach", "oily_or_smelly_stools", "sleep_problems", "less_urine",
    "decreased_mental_sharpness", "muscle_cramps", "dry_itchy_skin",
    "hypertension", "pain_in_the_belly", "diarrhoea", "dehydration",
    "back_or_side_pain", "blood_in_your_urine", "bloating", "increased_abdomen_size",
    "kidney_stones", "kidney_failure", "urinary_tract_infections", "severe_sharp_pain",
    "chills", "difficulty_in_passing_urine"
]

def correct_spelling(description):
    """
    Corrects spelling mistakes in the input description based on predefined symptoms.
    """
    words = word_tokenize(description.lower())
    corrected_words = [get_close_matches(word, SYMPTOMS_LIST, n=1, cutoff=0.8)[0] if get_close_matches(word, SYMPTOMS_LIST, n=1, cutoff=0.8) else word for word in words]
    return " ".join(corrected_words)

def extract_symptoms(description):
    """
    Extracts symptoms from the description after correcting spelling.
    """
    corrected_description = correct_spelling(description)
    words = word_tokenize(corrected_description)  # Tokenize words
    detected_symptoms = list(set(words) & set(SYMPTOMS_LIST))  # Find matching symptoms
    return ", ".join(detected_symptoms)  # Return as a comma-separated string

@login_required(login_url='patientlogin')
@user_passes_test(is_patient)
def patient_book_appointment_view(request):
    appointmentForm = forms.PatientAppointmentForm()
    patient = models.Patient.objects.get(user_id=request.user.id)  # Get patient info for sidebar
    message = None

    if request.method == 'POST':
        appointmentForm = forms.PatientAppointmentForm(request.POST)
        if appointmentForm.is_valid():
            desc = request.POST.get('description')

            # Step 1: Correct Spelling & Extract Symptoms
            extracted_symptoms = extract_symptoms(desc)
            print(f"Extraction symptoms:{extract_symptoms}")
            # Step 2: Predict Disease
            predicted_disease = predict_disease(extracted_symptoms.split(','))
            print(f"Prediction disieease:{predict_disease}")
            # Step 3: Save Prediction to `PatientPrediction`
            patient_prediction = models.PatientPrediction.objects.create(
                patient=patient,
                symptoms=extracted_symptoms,
                predicted_disease=predicted_disease
            )

            # Step 4: Save Appointment with Extracted Symptoms
            appointment = appointmentForm.save(commit=False)
            appointment.doctorId = request.POST.get('doctorId')
            appointment.patientId = request.user.id  # Ensure only their info is stored
            appointment.doctorName = models.User.objects.get(id=request.POST.get('doctorId')).first_name
            appointment.patientName = request.user.first_name
            appointment.symptoms = extracted_symptoms  # Store extracted symptoms
            appointment.status = False
            appointment.save()

            return HttpResponseRedirect('patient-view-appointment')

    mydict = {'appointmentForm': appointmentForm, 'patient': patient, 'message': message}
    return render(request, 'hospital/patient_book_appointment.html', context=mydict)


@login_required(login_url='patientlogin')
@user_passes_test(is_patient)
def patient_view_appointment_view(request):
    patient=models.Patient.objects.get(user_id=request.user.id) #for profile picture of patient in sidebar
    appointments=models.Appointment.objects.all().filter(patientId=request.user.id)
    return render(request,'hospital/patient_view_appointment.html',{'appointments':appointments,'patient':patient})



@login_required(login_url='patientlogin')
@user_passes_test(is_patient)
def patient_discharge_view(request):
    patient=models.Patient.objects.get(user_id=request.user.id) #for profile picture of patient in sidebar
    dischargeDetails=models.PatientDischargeDetails.objects.all().filter(patientId=patient.id).order_by('-id')[:1]
    patientDict=None
    if dischargeDetails:
        patientDict ={
        'is_discharged':True,
        'patient':patient,
        'patientId':patient.id,
        'patientName':patient.get_name,
        'assignedDoctorName':dischargeDetails[0].assignedDoctorName,
        'address':patient.address,
        'mobile':patient.mobile,
        'symptoms':patient.symptoms,
        'admitDate':patient.admitDate,
        'releaseDate':dischargeDetails[0].releaseDate,
        'daySpent':dischargeDetails[0].daySpent,
        'medicineCost':dischargeDetails[0].medicineCost,
        'roomCharge':dischargeDetails[0].roomCharge,
        'doctorFee':dischargeDetails[0].doctorFee,
        'OtherCharge':dischargeDetails[0].OtherCharge,
        'total':dischargeDetails[0].total,
        }
        print(patientDict)
    else:
        patientDict={
            'is_discharged':False,
            'patient':patient,
            'patientId':request.user.id,
        }
    return render(request,'hospital/patient_discharge.html',context=patientDict)



# for viewing the prescription
from hospital.models import Prescription, Patient
@login_required(login_url='patientlogin')
@user_passes_test(is_patient)
def patient_view_prescription(request):
    # Fetch the logged-in patient
    patient = get_object_or_404(Patient, user_id=request.user.id)
    
    # Fetch prescriptions related to the patient
    prescriptions = Prescription.objects.filter(patient=patient).order_by('-prescribed_date')

    return render(request, 'hospital/patient_view_prescription.html', {
        'patient': patient,
        'prescriptions': prescriptions
    })


#--------------------------------------------------------------------------------
#------------------------ PATIENT RELATED VIEWS END ------------------------------
#---------------------------------------------------------------------------------


#---------------------------------------------------------------------------------
#------------------------ ABOUT US AND CONTACT US VIEWS START --------------------
# ---------------------------------------------------------------------------
def aboutus_view(request):
    return render(request,'hospital/aboutus.html')

def contactus_view(request):
    sub = forms.ContactusForm()
    if request.method == 'POST':
        sub = forms.ContactusForm(request.POST)
        if sub.is_valid():
            email = sub.cleaned_data['Email']
            name=sub.cleaned_data['Name']
            message = sub.cleaned_data['Message']
            send_mail(str(name)+' || '+str(email),message,settings.EMAIL_HOST_USER, settings.EMAIL_RECEIVING_USER, fail_silently = False)
            return render(request, 'hospital/contactussuccess.html')
    return render(request, 'hospital/contactus.html', {'form':sub})
