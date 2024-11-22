from dataclasses import dataclass
from typing import Optional
import logging


@dataclass
class WifiInfo:
    ap_name: Optional[str] = None
    signal: Optional[float] = None
    channel: Optional[int] = None
    ap_mac: Optional[str] = None

    @classmethod
    def from_string(cls, wifi_info: str) -> "WifiInfo":
        try:
            ap_name, signal, channel, ap_mac = wifi_info.split(",")
            return cls(
                ap_name=ap_name,
                signal=float(signal),
                channel=int(channel),
                ap_mac=ap_mac.replace(":", ""),
            )
        except (ValueError, IndexError) as e:
            logging.warning(f"Failed to parse wifi info: {e}")
            return cls()
