import random
import datetime
import heapq

def fit_probability_distribution(relative_frequencies_dictionary):
    """Return a probability distribution fitted to the given relative-frequencies dictionary.

    This helper function is used in various config files.
    """
    frequencies_sum = float(sum(relative_frequencies_dictionary.values()))
    probabilities = dict()
    for k in relative_frequencies_dictionary.keys():
        frequency = relative_frequencies_dictionary[k]
        probability = frequency / frequencies_sum
        probabilities[k] = probability
    fitted_probability_distribution = dict()
    current_bound = 0.0
    for k in probabilities:
        probability = probabilities[k]
        probability_range_for_k = (current_bound, current_bound + probability)
        fitted_probability_distribution[k] = probability_range_for_k
        current_bound += probability
    # Make sure the last bound indeed extends to 1.0
    last_bound_attributed = list(probabilities)[-1]
    fitted_probability_distribution[last_bound_attributed] = (
        fitted_probability_distribution[last_bound_attributed][0], 1.0
    )
    return fitted_probability_distribution

def clamp(val, minimum, maximum):
    """Clamp numerical value between a [min, max] interval"""
    return max(minimum, min(val, maximum))

def get_random_day_of_year(year):
    """Return a randomly chosen day in the given year."""
    ordinal_date_on_jan_1_of_this_year = datetime.date(year, 1, 1).toordinal()
    ordinal_date = (
        ordinal_date_on_jan_1_of_this_year + random.randint(0, 365)
    )
    return datetime.date.fromordinal(ordinal_date)

def is_leap_year(year):
    """Return True if year is a leap year

    source: https://en.wikipedia.org/wiki/Gregorian_calendar
    """
    divisible_by_4 = year % 4 == 0
    divisible_by_100 = year % 100 == 0
    divisible_by_400 = year % 400 == 0

    # Leap years in the Gregorian calendar was
    # introduces in 1582
    if year < 1582:
        return False

    if divisible_by_400 or (divisible_by_4 and not divisible_by_100):
        return True

    return False

class PriorityQueue:
    """A helper class used when generating a town layout."""

    def __init__(self):
        """Initialize a PriorityQueue object."""
        self.elements = []

    def empty(self):
        """Return true if no elements are in the queue"""
        return len(self.elements) == 0

    def put(self, item, priority):
        """Add an item to the queue"""
        heapq.heappush(self.elements, (priority, item))

    def get(self):
        """Retrieve an item from the queue"""
        return heapq.heappop(self.elements)[1]
