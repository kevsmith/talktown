class EventBroadcaster:
    """Subscribe to event creations

    This class uses a singletopn pattern for
    ease of use within the program

    This class is mainly used by agents within Talk of the Town
    who create new events while interacting in the simuation
    """

    __instance = None

    @staticmethod
    def getInstance():
        if EventBroadcaster.__instance is None:
            EventBroadcaster

    @staticmethod
    def register_event(topic, event):
        """Broadcast an event out to event listeners"""

    def __init__(self):
        if EventBroadcaster.__instance is not None:
            raise Exception("EventBroadcaster is a singleton")
        else:
            EventBroadcaster.__instance = self
