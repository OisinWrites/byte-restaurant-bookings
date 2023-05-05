from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from django.http import HttpResponseBadRequest, HttpResponse
from django.db.models import Q
from django.urls import reverse
from django.utils.timezone import make_aware

from datetime import datetime, time, timedelta

from .forms import BookingForm, TableForm
from .models import Booking, Table, TableAvailability


def bookings(request, booking_id=None):
    """Initialise empty list for bookings to populate later"""
    successful_bookings = []

    """Initialises the booking variable to none, looks for new id"""
    booking = None
    if booking_id:
        booking = get_object_or_404(Booking, id=booking_id)

    """Code triggeered by form submission.
        Saves instance of the form as the booking variable,
        takes in the current user."""
    if request.method == 'POST':
        form = BookingForm(request, request.POST, instance=booking)
        if form.is_valid():
            booking = form.save(commit=False)
            booking.user = request.user
            """Validate start time and add error if fails"""
            start_time = form.cleaned_data['start_time']
            if start_time < timezone.now():
                form.add_error('start_time',
                               "Whoops! You're already late"
                               " for dinner. "
                               "Choose a day that hasn't happened yet."
                               )
            """Generates end time from start time for use by availabilities
                model to create a time slot"""
            end_time = start_time + timedelta(minutes=105)
            size_of_party = form.cleaned_data['size_of_party']
            """Order tables by size so that the smallest suitable
                table possible is selected first"""
            tables = Table.objects.filter(size__gte=size_of_party) \
                .order_by('size')
            """Checks if booking request clashes with existing booking slot"""
            for table in tables:
                table_availabilities = TableAvailability.objects.filter(
                    table=table,
                    start_time__lt=end_time,
                    end_time__gt=start_time,
                )
                """If not then saves the bookings and
                    creates and saved a slot"""
                if not table_availabilities:
                    booking.table = table
                    booking.end_time = end_time
                    booking.save()
                    successful_bookings.append(booking)
                    booking_instance = Booking.objects.get(id=booking.id)
                    table_availability = TableAvailability(
                        table=table,
                        start_time=start_time,
                        end_time=end_time,
                        booking_id=booking
                    )
                    table_availability.save()
                    messages.success(request, 'Your booking has been made.')
                    return redirect('bookings')
                    """Else error handling"""
            form.add_error('size_of_party', 'No table is available'
                           ' for the requested'
                           ' time and party size.'
                           ' Please select a new time.')
        else:
            """Error handling if form invalid"""
            form.add_error(None, 'There was an error with your booking.')
    else:
        """Where no id is found form returns to initial state"""
        form = BookingForm(request, instance=booking)

    """Creates list of bookings not older than current date for
        logged in user"""
    current_bookings = Booking.objects.filter(
        Q(start_time__gte=timezone.now()) | Q(
            user_id=request.user.id)).order_by('start_time')

    """Context list to call on these variables from the template"""
    context = {
        'form': form,
        'current_bookings': current_bookings,
        'successful_bookings': successful_bookings,
        'edit_booking': booking,
        # pass the booking to the template if it exists
    }
    return render(request, 'bookings/bookings.html', context)


def edit_booking(request, booking_id):

    """Creates the list of successful bookings"""
    successful_bookings = []

    """Searches for id"""
    booking = get_object_or_404(Booking, id=booking_id)

    """Handles a foreign user attempt to view the booking
        through url search with object id"""
    if booking.user != request.user:
        raise Http404("Booking not found")

    """Initiates form validation as before on form submission"""
    if request.method == 'POST':
        form = BookingForm(request, request.POST, instance=booking)
        if form.is_valid():
            booking = form.save(commit=False)
            start_time = form.cleaned_data['start_time']
            if start_time < timezone.now():
                form.add_error('start_time',
                               "Whoops! You're already late"
                               " for dinner. "
                               "Choose a day that hasn't happened yet."
                               )
            end_time = start_time + timedelta(minutes=105)
            size_of_party = form.cleaned_data['size_of_party']
            tables = Table.objects.filter(size__gte=size_of_party) \
                .order_by('size')
            for table in tables:
                table_availabilities = TableAvailability.objects.filter(
                    table=table,
                    start_time__lt=end_time,
                    end_time__gt=start_time
                )
                if not table_availabilities:
                    """When the booking is edited by time, the old
                    time slot needs to be edited, or replaced.
                    This code opts to delete the slot, in any case,
                    even if the edit is for party size only"""
                    TableAvailability.objects.filter(
                        id_of_booking=booking.id).delete()

                    booking.end_time = start_time + timedelta(minutes=105)
                    booking.table = table
                    booking.start_time = start_time
                    booking.save()

                    table_availability = TableAvailability(
                        table=table,
                        start_time=start_time,
                        end_time=booking.end_time,
                        booking_id=booking,
                    )
                    table_availability.save()
                    """Booking edit saved, and new time slot created"""
                    successful_bookings.append(booking)
                    messages.success(request, 'Your booking has been updated.')
                    return redirect('bookings')
            form.add_error('size_of_party', 'No table is available'
                           ' for the requested'
                           ' time and party size.'
                           ' Please select a new time.')
        else:
            form.add_error(None, 'There was an error with your booking.')
    else:
        form = BookingForm(request, instance=booking)

    current_bookings = Booking.objects.filter(
        Q(start_time__gte=timezone.now()) | Q(
            user_id=request.user.id)).order_by('start_time')

    context = {
        'form': form,
        'current_bookings': current_bookings,
        'successful_bookings': successful_bookings,
        'edit_booking': booking,
        # pass the booking to the template if it exists
    }

    return render(request, 'bookings/edit_booking.html', context)


def delete_booking(request, booking_id):
    """Identify object by id"""
    booking = get_object_or_404(Booking, id=booking_id, user=request.user)
    """Finds and deletes by detail match"""
    table_availability = TableAvailability.objects.filter(
        table=booking.table,
        start_time=booking.start_time,
        end_time=booking.end_time
    ).delete()
    booking.delete()
    """Returns success and reverses url, as current url no longer
    valid as booking object id was populating the end of the url"""
    messages.success(request, 'Your booking has been deleted.')
    return redirect(reverse('bookings'))


"""This is a convoluted view that essentially melds two purposes
    so as to confine the admin CRUD abilities to a single html file.
    This view iterates the existing bookings, through search and
    filter methods. It allows the admin to view, create, and delete tables
    for the restaurant, but not edit them as quick deletiong and recreation
    was deemed sufficient for this particularly simple model."""


def bookings_management(request):

    """Handles the table creation form of just the table size input."""
    if request.method == 'POST':
        form = TableForm(request.POST)
        if form.is_valid():
            table = form.save(commit=False)
            table.save()
            messages.success(request, 'New table added to seating plan.')
            return redirect('bookings_management')
    else:
        form = TableForm()

    def next_day(date):
        """Returns the next day from a given date."""
        next_day = date + timedelta(days=1)
        return make_aware(datetime(next_day.year,
                          next_day.month, next_day.day, 0, 0, 0))

    tables = Table.objects.all().order_by('number')

    """Get search query from request"""
    search_query = request.GET.get('search', '')

    """Get filter query from request"""
    filter_query = request.GET.get('filter', '')

    """Set the date range for filter"""
    now = datetime.now()
    today = make_aware(datetime(now.year, now.month, now.day, 0, 0, 0))
    next_week = today + timedelta(days=7)

    """Filter bookings by not earlier than the current day"""
    bookings = Booking.objects.filter(start_time__gte=today)

    """Filter bookings by user name if search query is provided"""
    if search_query:
        bookings = bookings.filter(user__username__icontains=search_query)

    """Filter bookings by day or week if filter query is provided"""
    if filter_query == 'day':
        start_date = today
        end_date = next_day(start_date)
        bookings = bookings.filter(start_time__range=(start_date, end_date))
    elif filter_query == 'week':
        start_date = today
        end_date = start_date + timedelta(days=7)
        bookings = bookings.filter(start_time__range=(start_date, end_date))
    elif filter_query == 'all':

        """Order the bookings by user name,
            size of party, start time and date"""
            
        bookings = bookings.order_by('user__username',
                                     'size_of_party', 'start_time')

    context = {
        'table_form': form,
        'bookings': bookings,
        'filter_query': filter_query,
        'search_query': search_query,
        'tables': tables
    }

    return render(request, 'bookings/bookings_management.html', context)


"""Simple model deletion with message.
    However, deletion of a table will result in the collapse
    of all associated bookings and time slots for all bookings
    through the cascade method.
    A warning should be implemented to the admin before aggreeing
    to delete a table. Alternatively the edit_booking function could be
    used to automatically attempt to reconstitute bookings keeping
    date/time and party-size unaltered."""


def delete_table(request, table_id):
    table = get_object_or_404(Table, id=table_id)
    table.delete()
    messages.success(request, 'Your table has been deleted.')
    return redirect(reverse('bookings_management'))
