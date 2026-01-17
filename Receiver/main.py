#!/usr/bin/env python3
"""
OpenCtrl / Receiver

A macOS HID event logger using CGEventTap.
This script captures and logs keyboard and mouse events in real-time.
It can optionally suppress events to prevent them from reaching the OS.

Features:
- Logs keyboard events with key pressed and modifier keys (Shift, Ctrl, etc.)
- Logs mouse movements, clicks, and scroll events
- Kill switch: Press 'q' to stop the logger
- Suppression mode: Use --catch to block events from reaching the OS
"""

import argparse
import sys
import time

import Quartz
import CoreFoundation

# Global flag for kill switch - set to True to stop the event loop
kill_switch_flag = False

# Dictionary mapping Quartz event constants to readable names
EVENT_TYPE_NAMES = {
    Quartz.kCGEventKeyDown:           "KeyDown          ",
    Quartz.kCGEventKeyUp:             "KeyUp            ",
    Quartz.kCGEventMouseMoved:        "MouseMoved       ",
    Quartz.kCGEventLeftMouseDown:     "LeftMouseDown    ",
    Quartz.kCGEventLeftMouseUp:       "LeftMouseUp      ",
    Quartz.kCGEventRightMouseDown:    "RightMouseDown   ",
    Quartz.kCGEventRightMouseUp:      "RightMouseUp     ",
    Quartz.kCGEventOtherMouseDown:    "OtherMouseDown   ",
    Quartz.kCGEventOtherMouseUp:      "OtherMouseUp     ",
    Quartz.kCGEventScrollWheel:       "ScrollWheel      ",
    Quartz.kCGEventLeftMouseDragged:  "LeftMouseDragged ",
    Quartz.kCGEventRightMouseDragged: "RightMouseDragged",
    Quartz.kCGEventOtherMouseDragged: "OtherMouseDragged",
}


def get_event_type_name(event_type: int) -> str:
    """Convert a Quartz event type constant to a human-readable string."""
    return EVENT_TYPE_NAMES.get(event_type, f"EventType({event_type})")


def get_key_string(event) -> str:
    """
    Convert a keyboard event to a readable string.
    Tries to get the Unicode character first, falls back to keycode.
    """
    try:
        # Get the Unicode string for the key
        length, string = Quartz.CGEventKeyboardGetUnicodeString(event, 4, None, None)
        if length > 0:
            return string[:length]
    except Exception:
        pass

    # Fallback to keycode if Unicode conversion fails
    keycode = Quartz.CGEventGetIntegerValueField(event, Quartz.kCGKeyboardEventKeycode)
    return f"<keycode {keycode}>"


def get_modifier_string(flags: int) -> str:
    """Convert modifier flags to a readable string (e.g., 'Shift+Ctrl')."""
    modifiers = []
    if flags & Quartz.kCGEventFlagMaskShift:
        modifiers.append("Shift")
    if flags & Quartz.kCGEventFlagMaskControl:
        modifiers.append("Ctrl")
    if flags & Quartz.kCGEventFlagMaskAlternate:
        modifiers.append("Alt")
    if flags & Quartz.kCGEventFlagMaskCommand:
        modifiers.append("Cmd")
    if flags & Quartz.kCGEventFlagMaskAlphaShift:
        modifiers.append("CapsLock")
    if flags & Quartz.kCGEventFlagMaskHelp:
        modifiers.append("Help")
    if flags & Quartz.kCGEventFlagMaskSecondaryFn:
        modifiers.append("Fn")
    if flags & Quartz.kCGEventFlagMaskNumericPad:
        modifiers.append("NumPad")

    return "+".join(modifiers) if modifiers else "None"


def get_mouse_location(event) -> str:
    """Extract and format mouse coordinates from an event."""
    location = Quartz.CGEventGetLocation(event)
    return f"x={int(location.x)} y={int(location.y)}"


def get_scroll_delta(event) -> str:
    """Extract and format scroll wheel deltas from an event."""
    delta_y = Quartz.CGEventGetIntegerValueField(event, Quartz.kCGScrollWheelEventDeltaAxis1)
    delta_x = Quartz.CGEventGetIntegerValueField(event, Quartz.kCGScrollWheelEventDeltaAxis2)
    return f"dx={delta_x} dy={delta_y}"


def event_callback(proxy, event_type, event, refcon):
    """
    Callback function called for each intercepted HID event.

    Args:
        proxy: The event tap proxy
        event_type: Type of the event (key, mouse, etc.)
        event: The CGEvent object
        refcon: Reference constant (used for suppression flag)

    Returns:
        The event (to pass it through) or None (to suppress it)
    """
    global kill_switch_flag
    suppress_events = bool(refcon)

    # Handle tap timeout - re-enable if needed
    if event_type == Quartz.kCGEventTapDisabledByTimeout:
        Quartz.CGEventTapEnable(proxy, True)
        return event

    event_name = get_event_type_name(event_type)

    # Handle keyboard events
    if event_type in (Quartz.kCGEventKeyDown, Quartz.kCGEventKeyUp):
        key_pressed = get_key_string(event)
        modifier_flags = Quartz.CGEventGetFlags(event)
        modifiers = get_modifier_string(modifier_flags)

        # Check for kill switch on key down
        if event_type == Quartz.kCGEventKeyDown and key_pressed.lower() == "q":
            kill_switch_flag = True
            print("\nKill-switch activated: 'q' pressed. Stopping logger.")
            return None

        print(f"[Keyboard][{event_name}] {key_pressed} [{modifiers}]")

    # Handle mouse movement and click events
    elif event_type in (
        Quartz.kCGEventMouseMoved,
        Quartz.kCGEventLeftMouseDragged,
        Quartz.kCGEventRightMouseDragged,
        Quartz.kCGEventOtherMouseDragged,
        Quartz.kCGEventLeftMouseDown,
        Quartz.kCGEventLeftMouseUp,
        Quartz.kCGEventRightMouseDown,
        Quartz.kCGEventRightMouseUp,
        Quartz.kCGEventOtherMouseDown,
        Quartz.kCGEventOtherMouseUp,
    ):
        print(f"[Mouse   ][{event_name}] {get_mouse_location(event)}")

    # Handle scroll wheel events
    elif event_type == Quartz.kCGEventScrollWheel:
        print(f"[Mouse   ][{event_name}] {get_scroll_delta(event)}")
    # Handle any other events
    else:
        print(f"[Event   ][{event_name}]")

    # Return None to suppress the event, or the event to pass it through
    return None if suppress_events else event


def create_event_mask() -> int:
    """Create a bitmask for the types of events we want to intercept."""
    events_to_capture = [
        Quartz.kCGEventKeyDown,
        Quartz.kCGEventKeyUp,
        Quartz.kCGEventMouseMoved,
        Quartz.kCGEventLeftMouseDown,
        Quartz.kCGEventLeftMouseUp,
        Quartz.kCGEventRightMouseDown,
        Quartz.kCGEventRightMouseUp,
        Quartz.kCGEventOtherMouseDown,
        Quartz.kCGEventOtherMouseUp,
        Quartz.kCGEventLeftMouseDragged,
        Quartz.kCGEventRightMouseDragged,
        Quartz.kCGEventOtherMouseDragged,
        Quartz.kCGEventScrollWheel,
    ]

    mask = 0
    for event_type in events_to_capture:
        mask |= Quartz.CGEventMaskBit(event_type)
    return mask


def main() -> int:
    """Main function - parse arguments and start the event logger."""
    parser = argparse.ArgumentParser(
        description="macOS HID event logger using CGEventTap",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py              # Log events without suppressing them
  python main.py --catch      # Log and suppress events (blocks OS input)
        """
    )
    parser.add_argument(
        "--catch",
        action="store_true",
        help="Suppress events (prevent them from reaching the OS)",
    )
    args = parser.parse_args()

    suppress_events = args.catch

    # Create the event tap to intercept HID events
    event_mask = create_event_mask()
    event_tap = Quartz.CGEventTapCreate(
        Quartz.kCGHIDEventTap,        # Tap at HID level
        Quartz.kCGHeadInsertEventTap, # Insert at head of event stream
        Quartz.kCGEventTapOptionDefault,
        event_mask,
        event_callback,
        suppress_events,
    )

    if not event_tap:
        print(
            "Error: Failed to create event tap.\n"
            "Please grant Accessibility permissions in System Settings > Privacy & Security.",
            file=sys.stderr,
        )
        return 1

    # Set up the run loop to process events
    run_loop_source = Quartz.CFMachPortCreateRunLoopSource(None, event_tap, 0)
    CoreFoundation.CFRunLoopAddSource(
        CoreFoundation.CFRunLoopGetCurrent(),
        run_loop_source,
        CoreFoundation.kCFRunLoopCommonModes,
    )
    Quartz.CGEventTapEnable(event_tap, True)

    print("HID Event Logger started.")
    print(f"Event suppression: {'ON' if suppress_events else 'OFF'}")
    print("Press 'q' to stop logging.")

    # Main event loop
    try:
        while not kill_switch_flag:
            CoreFoundation.CFRunLoopRunInMode(
                CoreFoundation.kCFRunLoopDefaultMode, 0.25, False
            )
            time.sleep(0.01)
    except KeyboardInterrupt:
        print("\nLogger stopped by interrupt.")
        return 0

    print("Logger stopped.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())