from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any, Dict, Optional

import numpy as np
import pandas as pd
import requests
import xmltodict

from src.db.engine import DBWriter
from src.settings import get_service_key

logger = logging.getLogger("airport.ingest.external")


class ExternalDataIngestor:
    """
    Handles fetching, parsing, and persisting data from external sources like
    the METAR weather API and the passenger forecast API.
    """

    def __init__(self, db_writer: DBWriter):
        """
        Initializes the ingestor.

        Args:
            db_writer: A DBWriter instance for persisting data.
        """
        self.db_writer = db_writer
        self.metar_url = "https://apis.data.go.kr/1360000/AmmService/getMetar"
        self.passenger_url = "https://apis.data.go.kr/B551177/passgrAnncmt/getPassgrAnncmt"
        self.metar_icao = "RKSI"  # Incheon International Airport

        # Fallback pattern for schedule density if DB lookup fails
        self.schedule_density_pattern = {
            '00_01': 0.1, '01_02': 0.05, '02_03': 0.05, '03_04': 0.1,
            '04_05': 0.3, '05_06': 0.7, '06_07': 1.0, '07_08': 0.9,
            '08_09': 0.8, '09_10': 0.7, '10_11': 0.6, '11_12': 0.6,
            '12_13': 0.6, '13_14': 0.7, '14_15': 0.8, '15_16': 0.9,
            '16_17': 1.0, '17_18': 0.9, '18_19': 0.8, '19_20': 0.7,
            '20_21': 0.5, '21_22': 0.4, '22_23': 0.3, '23_00': 0.2
        }

    def fetch_and_process_metar(self) -> Optional[Dict[str, Any]]:
        """
        Fetches the latest METAR report, parses it, persists it, and returns the parsed data.

        Returns:
            A dictionary with parsed weather data (temp, rain_flag, rain_mm) or None on failure.
        """
        params = {
            "serviceKey": get_service_key('kma'),
            "pageNo": 1,
            "numOfRows": 1,
            "dataType": "XML",
            "icao": self.metar_icao,
        }
        try:
            resp = requests.get(self.metar_url, params=params, timeout=10)
            resp.raise_for_status()
            data = xmltodict.parse(resp.content)
            item = data.get("response", {}).get("body", {}).get("items", {}).get("item")
            if not item:
                logger.warning("METAR API returned no items.")
                return None

            metar_msg = item.get("metarMsg", "")
            parsed_weather = self._parse_metar_message(metar_msg)

            record = {
                "icao": self.metar_icao,
                "metar_msg": metar_msg,
                "temp": parsed_weather["temp"],
                "rain_flag": parsed_weather["rain_flag"],
                "rain_mm": parsed_weather["rain_mm"],
                "raw_json": json.dumps(item, ensure_ascii=False),
                "collected_at": datetime.now(),
            }
            self.db_writer.insert_df("metar_raw", pd.DataFrame([record]))
            return parsed_weather
        except requests.RequestException as e:
            logger.error(f"Failed to fetch METAR data: {e}")
            return None

    def fetch_and_process_passenger_forecast(self, select_date: int = 0) -> Optional[pd.DataFrame]:
        """
        Fetches passenger forecast for a given date, persists the raw and transformed data.

        Args:
            select_date: 0 for today, 1 for tomorrow, etc.

        Returns:
            A DataFrame with the transformed T1 passenger forecast, or None on failure.
        """
        params = {
            "serviceKey": get_service_key('default'),
            "selectdate": select_date,
            "type": "xml",
        }
        try:
            resp = requests.get(self.passenger_url, params=params, timeout=10)
            resp.raise_for_status()
            data = xmltodict.parse(resp.content)
            items = data.get("response", {}).get("body", {}).get("items", {}).get("item", [])
            if not items:
                logger.warning("Passenger forecast API returned no items.")
                return None

            df_raw = pd.DataFrame(items)
            df_raw = df_raw[df_raw["adate"] != "합계"].copy()
            df_raw["collected_at"] = datetime.now()
            
            # Persist raw data with all columns
            raw_records = []
            for _, row in df_raw.iterrows():
                rec = row.to_dict()
                rec["raw_json"] = json.dumps(rec, ensure_ascii=False)
                raw_records.append(rec)
            
            if raw_records:
                self.db_writer.insert_df("passenger_forecast_raw", pd.DataFrame(raw_records))

            # Transform for T1 and persist
            df_t1 = self._transform_passenger_t1(df_raw)
            if not df_t1.empty:
                self.db_writer.insert_df("passenger_forecast_t1", df_t1)
            
            return df_t1
        except requests.RequestException as e:
            logger.error(f"Failed to fetch passenger forecast data: {e}")
            return None

    def _transform_passenger_t1(self, df_raw: pd.DataFrame) -> pd.DataFrame:
        """Transforms raw forecast data into a clean format for Terminal 1."""
        rows = []
        for _, row in df_raw.iterrows():
            for i in range(1, 7):
                col = f"t1dg{i}"
                val = self._safe_float(row.get(col))
                if val is not None:
                    rows.append({
                        "date": row.get("adate"),
                        "time_slot": row.get("atime"),
                        "departure_gate": f"DG{i}",
                        "expected_passenger_load": val,
                        "collected_at": row["collected_at"],
                    })
        return pd.DataFrame(rows)

    def _parse_metar_message(self, metar_msg: str) -> Dict[str, Any]:
        """
        Parses a METAR string to extract temperature and rain information.
        Example: RKSI 270100Z 27006KT 9999 FEW030 15/09 Q1013 NOSIG
        """
        if not isinstance(metar_msg, str):
            return {"temp": np.nan, "rain_flag": 0, "rain_mm": 0.0}

        temp, rain_flag, rain_mm = np.nan, 0, 0.0
        try:
            parts = metar_msg.split()
            for part in parts:
                if "/" in part and ("M" in part or part[0].isdigit()):
                    temp_part = part.split("/")[0]
                    if temp_part.startswith("M"):
                        temp = -int(temp_part[1:])
                    else:
                        temp = int(temp_part)
                    break
            
            rain_keywords = ['RA', 'SN', 'DZ', 'SH', 'TS', 'GS', 'GR', 'PL']
            if any(keyword in metar_msg for keyword in rain_keywords):
                rain_flag = 1
                if 'RA+' in metar_msg or 'TSRA' in metar_msg:
                    rain_mm = 10.0  # Heavy rain
                elif 'RA' in metar_msg or 'SHRA' in metar_msg:
                    rain_mm = 2.0   # Moderate rain
                else:
                    rain_mm = 1.0   # Light precipitation
        except (ValueError, IndexError) as e:
            logger.warning(f"Could not parse METAR message '{metar_msg}': {e}")
        
        return {"temp": temp, "rain_flag": rain_flag, "rain_mm": rain_mm}

    def get_schedule_density_fallback(self, time_slot: str) -> float:
        """Provides a fallback schedule density based on a predefined pattern."""
        return float(self.schedule_density_pattern.get(time_slot, 0.5))

    @staticmethod
    def _safe_float(x: Any) -> Optional[float]:
        try:
            return float(x)
        except (ValueError, TypeError):
            return None