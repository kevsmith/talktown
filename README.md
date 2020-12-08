# talktown
A generator of American small towns, with an emphasis on social simulation.

This code has been modified from the original repo to run using python3.


## Running The Test Script

```bash
# Just run the test script and print story sifting results
$ python ./test.py

# Run the test script and open the python
# interpreter to inspect the simulation
$ python -i ./test.py

# Example output:

# Generating a town...
# Simulating 140 years of history...
# Wrapping up...
# After 93s, town generation was successful!
#
# It is now the day of August 19, 1979, in the town of Palmer, # pop. 242.
#
# Excavating nuggets of dramatic intrigue...
#         Found 118 cases of unrequited love
#         Found 0 love triangles
#         Found 25 cases of extramarital romantic interest
#         Found 8 asymmetric friendships
#         Found 0 misanthropes
#         Found 0 character rivalries
#         Found 0 sibling rivalries
#         Found 60 business-owner rivalries
```

## Exporting the Simulation

There is support for serializing the state of the simulation into JSON. This is accomplished by using the talktown.serializer module. It supports creating JSON strings and writing them to file.

```python
# Example Serialization

from talktown.simulation import Simulation
import talktown.serializer as serializer


sim = Simulation() # create simulation

... # update simulation

# Write the final state to JSON
serializer.serialize_to_file(sim, "./out/town.json")

```

Below is a sample of the JSON format used when serializing talktown simulations.

```javascript
// Talktown JSON Format
{
        // simulation properties
        "year": int,
        "true_year": int,
        "ordinal_date": int,
        "month": int,
        "day": int,
        "time_of_day": string,
        "weather": string,
        "last_simulated_day": int,
        "n_simulated_timesteps": int,
        "town": {
                "founded": int,
                "places": {
                        // Map place IDs to place data
                        "0": {
                                // place attributes
                        },
                        ...
                },
                "people": {
                        // Map people IDs to place data
                        "0": {
                                // people attributes
                        },
                        ...
                },
                "companies": {
                        // Map business IDs to place data
                        "0": {
                                // business attributes
                        },
                        ...
                },
                ... // Other town attributes
        },
        "events": {
                // Map event IDs to event data
                "0": {
                        // event attributes
                },
                ...
        },
        "birthdays": {
                // Maps a key with the month and
                // day (separated with underscore)
                "2_9": [int, int, ... ],
                "2_10": [int, int, ... ],
                ...
        }

}
```
## Notes

* For retconning, the time of day will always be whatever the actual time of day
is at the beginning of the true simulation ("day", I assume), but this shouldn't matter

* Being the town mayor doesn't relly mean anything

## References

Findings from these papers have been operationalized at various points in this project; wherever appropriate, a source that is operationalized by a block of code is cited in-line in a comment. For an example citation, see line 49 in relationship.py.


[0] Schmitt, et al. "Big Five Traits Across 56 Nations"

[1] Paulauskaitė1, et al. "Big Five Personality Traits Linked With Migratory Intentions In
        Lithuanian Student Sample"

[2] Reynolds and Pezdek. "Face Recognition Memory: The Effects of Exposure Duration and
        Encoding Instruction"

[3] Ruiz-Soler and Beltran. "The Relative Salience of Facial Features When Differentiating Faces
        Based on an Interference Paradigm"

[4] Selfhout et al. 2010: "Emerging late adolescent friendship networks and Big Five personality
        traits: a social network approach"

[5] Shanhong Luo and Guangjian Zhang. "What Leads to Romantic Attraction: Similarity, Reciprocity,
        Security, or Beauty? Evidence From a Speed-Dating Study"

[6] Wilson, R. M.; Gambrell, L. B.; and Pfeiffer, W. R. 1985. "The effects of retelling upon reading
        comprehension and recall of text information". The Journal of Educational Research 78(4):216–220.

[7] Verbrugge, L. M. (1977). The structure of adult friendship choices. Social forces, 56(2), 576-597.
