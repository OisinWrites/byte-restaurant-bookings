from django.db import models
from django.conf import settings
from django.contrib.auth.models import User


"""
This model manager is used to populate a table's id automatically
when a table object is created.
It searches for the lowest available number from 1 up.
There fore if there are tables 1-10, and 7 is deleted, the
next table will have a number of 7 instead of 11
"""


class TableManager(models.Manager):
    def get_lowest_available_number(self):
        used_numbers = self.values_list('number', flat=True)
        for i in range(1, len(used_numbers) + 2):
            if i not in used_numbers:
                return i


"""
The table model could be changed from the table size options
which are limiting, to a more fluid model. This would allow
the admin to add larger tables to their restaurant, or, given the
ability to edit, they could add or remove seats from tables.
"""


class Table(models.Model):
    TABLE_SIZES = (
        ('2', '2-seater'),
        ('4', '4-seater'),
        ('6', '6-seater'),
    )
    number = models.IntegerField(unique=True, blank=True,
                                 null=True, editable=False)
    size = models.CharField(max_length=1, choices=TABLE_SIZES)

    objects = TableManager()

    def __str__(self):
        return f'Table {self.number} ({self.get_size_display()})'

    def save(self, *args, **kwargs):
        if not self.pk:
            self.number = Table.objects.get_lowest_available_number()
        super().save(*args, **kwargs)


"""The booking model
Takes a table as a FK, generates an end time based on its start time
in the corresponding view. Takes email of user to verify what
bookings are accesssible to a authorised user later, takes a name as
a friendly version of email for that template,
takes in size of party to reflect to admin that a booking at
a table of 6 could be for 4 or 5 pax."""


class Booking(models.Model):
    """
    Booking model wants to know
    where, when, until, who, how many, anything else, verify,
    and assign itself a unique id.
    In this case the id's are not necessarily unique
    but generating sequentially
    from 1, and being uneditable are not clashing with sames instances.
    """
    table = models.ForeignKey(Table, on_delete=models.CASCADE, null=True)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField(null=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    size_of_party = models.IntegerField()
    additional = models.CharField(max_length=200, blank=True, null=True)
    email = models.EmailField(null=True)
    booking_id = models.CharField(max_length=10, null=True)

    def save(self, *args, **kwargs):
        self.email = self.user.email
        super().save(*args, **kwargs)
        self.booking_id = str(self.id)
        super().save(update_fields=['booking_id'])

    """Returns the reader friendly version of the booking"""
    def __str__(self):
        return f'{self.user.username} ({self.size_of_party} people)' \
               f' - {self.table} ' \
               f'- {self.start_time.strftime("%d-%m %H:%M")} to ' \
               f'{self.end_time.strftime("%d-%m %H:%M")}'


"""
This table availability model is to track the tables' availability at
given time and date, and presuming a table is otherwise always available in
the table model.

"""


class TableAvailability(models.Model):
    table = models.ForeignKey(Table, on_delete=models.CASCADE)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    booking_id = models.ForeignKey(Booking, on_delete=models.CASCADE,
                                   null=True, blank=True)
    id_of_booking = models.IntegerField(null=True, blank=True)

    """cos availabilitys is no good english"""
    class Meta:
        verbose_name_plural = 'Table Availabilities'

    """
    This function rips the id from the booking information
    assigned to this models booking_id attribute, and then
    saves it as id_of_booking, this allows for simulacrum
    of a cascade function in the edit view.
    """
    def save(self, *args, **kwargs):
        if self.booking_id:
            self.id_of_booking = self.booking_id.id
        super(TableAvailability, self).save(*args, **kwargs)
