import libvirt

Event_string = (
    ("Added", "Updated"),
    ("Removed"),
    ("Booted", "Migrated_when_boot", "Restored", "Snapshot", "Wakeup"),
    ("Paused", "Migrated_when_pause", "IOError", "Watchdog", "Restored", "Snapshot"),
    ("Unpaused", "Migrated_when_unpause", "Snapshot"),
    ("Shutdown", "Destroyed", "Crashed", "Migrated_when_shutoff", "Saved", "Failed", "Snapshot"),
    ("Finished", "Prepare-ShutOff")
    )

Event_failed = (Event_string[5][2], Event_string[5][5])
Event_destroyed = (Event_string[5][1],)
Event_migrated = (Event_string[5][3],) 

Event_watchdog_action = (
    libvirt.VIR_DOMAIN_EVENT_WATCHDOG_NONE,  # = 0, No action, watchdog ignored
    libvirt.VIR_DOMAIN_EVENT_WATCHDOG_PAUSE,  # = 1, Guest CPUs are paused
    # libvirt.VIR_DOMAIN_EVENT_WATCHDOG_RESET,  # = 2, Guest CPUs are reset
    libvirt.VIR_DOMAIN_EVENT_WATCHDOG_POWEROFF,  # = 3, Guest is forcibly powered off
    libvirt.VIR_DOMAIN_EVENT_WATCHDOG_SHUTDOWN,  # = 4, Guest is requested to gracefully shutdown
    libvirt.VIR_DOMAIN_EVENT_WATCHDOG_DEBUG,  # = 5, No action, a debug message logged
    libvirt.VIR_DOMAIN_EVENT_WATCHDOG_INJECTNMI,  # = 6, Inject a non-maskable interrupt into guest
    )
