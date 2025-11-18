#!/usr/bin/env python3
"""
Amplitude Analytics Data Extractor for Keboola

This component extracts raw event data from Amplitude and loads it into Keboola Storage.

Configuration:
- AMPLITUDE_API_KEY: Amplitude API key (encrypted)
- AMPLITUDE_SECRET_KEY: Amplitude secret key for Export API (encrypted)
- start_date: Start date in format YYYYMMDDTHH (e.g., 20251112T00)
- end_date: End date in format YYYYMMDDTHH (e.g., 20251113T00)
- output_table: Destination table in Keboola Storage (default: out.c-amplitude.events)

State file tracks:
- last_exported_end: Last successfully exported time range (for incremental loads)
- event_count: Number of events exported in last run
"""

import logging
import csv
import os
import json
import time
from datetime import datetime

try:
    from keboola.component import CommonInterface
    from keboola.component.dao import BaseType, ColumnDefinition
except ImportError:
    # For local testing, we'll handle this in sample_run.py
    pass
from amplitude_driver import AmplitudeDriver, ValidationError, TimeoutError, AuthenticationError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def get_schema():
    """Define the schema for Amplitude events"""
    return {
        "event_id": ColumnDefinition(data_types=BaseType.string()),
        "user_id": ColumnDefinition(data_types=BaseType.string()),
        "device_id": ColumnDefinition(data_types=BaseType.string()),
        "event_type": ColumnDefinition(data_types=BaseType.string()),
        "event_time": ColumnDefinition(data_types=BaseType.string()),
        "amplitude_id": ColumnDefinition(data_types=BaseType.string()),
        "platform": ColumnDefinition(data_types=BaseType.string()),
        "os_name": ColumnDefinition(data_types=BaseType.string()),
        "city": ColumnDefinition(data_types=BaseType.string()),
        "country": ColumnDefinition(data_types=BaseType.string()),
        "event_properties": ColumnDefinition(data_types=BaseType.string()),
        "user_properties": ColumnDefinition(data_types=BaseType.string()),
    }


def flatten_json(obj, parent_key='', sep='_'):
    """Flatten nested JSON objects to string representation"""
    import json
    if isinstance(obj, dict):
        return json.dumps(obj)
    return str(obj)


def export_amplitude_events(ci, amplitude_api_key, amplitude_secret_key, start_date, end_date, output_table):
    """
    Export events from Amplitude and write to Keboola output table

    Args:
        ci: CommonInterface instance
        amplitude_api_key: Amplitude API key
        amplitude_secret_key: Amplitude secret key
        start_date: Start date in format YYYYMMDDTHH
        end_date: End date in format YYYYMMDDTHH
        output_table: Destination table in Keboola Storage
    """
    logger.info(f"Starting Amplitude export: {start_date} → {end_date}")

    # Initialize Amplitude driver
    try:
        # Set environment variables for driver
        os.environ['AMPLITUDE_API_KEY'] = amplitude_api_key
        os.environ['AMPLITUDE_SECRET_KEY'] = amplitude_secret_key

        driver = AmplitudeDriver(
            api_key=amplitude_api_key,
            secret_key=amplitude_secret_key,
            region="standard"
        )
        logger.info("✓ Amplitude driver initialized")

    except AuthenticationError as e:
        logger.error(f"Authentication failed: {e.message}")
        raise
    except Exception as e:
        logger.error(f"Failed to initialize driver: {e}")
        raise

    # Export events
    try:
        logger.info(f"Exporting events from {start_date} to {end_date}...")
        events = driver.read_events_export(start=start_date, end=end_date)
        logger.info(f"✓ Exported {len(events)} events")

    except TimeoutError as e:
        logger.error(f"Export timed out: {e.message}")
        raise
    except ValidationError as e:
        logger.error(f"Validation error: {e.message}")
        raise
    except Exception as e:
        logger.error(f"Export failed: {e}")
        raise
    finally:
        driver.close()

    if not events:
        logger.warning("No events exported")
        return 0

    # Create output table definition
    out_table = ci.create_out_table_definition(
        name=output_table.split('.')[-1] + '.csv',  # e.g., "events.csv"
        destination=output_table,
        schema=get_schema(),
        incremental=False,
        has_header=True,
    )

    logger.info(f"Writing {len(events)} events to {out_table.full_path}")

    # Write events to CSV
    with open(out_table.full_path, 'w+', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(
            f,
            fieldnames=out_table.column_names,
            extrasaction='ignore',  # Ignore extra fields not in schema
        )
        writer.writeheader()

        for event in events:
            # Map Amplitude fields to our schema
            row = {
                "event_id": event.get('event_id', ''),
                "user_id": event.get('user_id', ''),
                "device_id": event.get('device_id', ''),
                "event_type": event.get('event_type', ''),
                "event_time": event.get('event_time', ''),
                "amplitude_id": event.get('amplitude_id', ''),
                "platform": event.get('platform', ''),
                "os_name": event.get('os_name', ''),
                "city": event.get('city', ''),
                "country": event.get('country', ''),
                "event_properties": flatten_json(event.get('event_properties', {})),
                "user_properties": flatten_json(event.get('user_properties', {})),
            }
            writer.writerow(row)

    logger.info(f"✓ Wrote {len(events)} events to CSV")

    # Write manifest
    ci.write_manifest(out_table)
    logger.info(f"✓ Manifest written to {out_table.full_path}.manifest")

    return len(events)


def update_state(ci, end_date, event_count):
    """Update state file for incremental runs"""
    state = {
        "last_exported_end": end_date,
        "event_count": event_count,
        "last_run": datetime.now().isoformat(),
    }
    ci.write_state_file(state)
    logger.info(f"✓ State updated: {event_count} events exported, next run from {end_date}")


def write_user_properties_from_table(ci, amplitude_api_key):
    """
    Read user properties from Keboola input table and write to Amplitude

    Args:
        ci: CommonInterface instance
        amplitude_api_key: Amplitude API key

    Returns:
        Number of user properties updated
    """
    logger.info("Starting user properties write to Amplitude")

    # Get configuration
    parameters = ci.configuration.parameters
    user_id_column = parameters.get('user_id_column', 'user_id')
    property_columns = parameters.get('property_columns', {})

    if not property_columns:
        logger.warning("No property_columns configured, skipping write")
        return 0

    # Get input tables
    input_tables = ci.get_input_tables_definitions()
    if not input_tables:
        logger.warning("No input tables found, skipping write")
        return 0

    # Use first input table
    input_table = input_tables[0]
    logger.info(f"Reading from input table: {input_table.name}")

    # Initialize Amplitude driver
    try:
        driver = AmplitudeDriver(api_key=amplitude_api_key)
        logger.info("✓ Amplitude driver initialized for write")
    except Exception as e:
        logger.error(f"Failed to initialize driver: {e}")
        raise

    # Read input CSV and prepare user property updates
    identifications = []
    row_count = 0

    try:
        with open(input_table.full_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)

            for row in reader:
                row_count += 1
                user_id = row.get(user_id_column)

                if not user_id:
                    logger.warning(f"Row {row_count}: Missing user_id_column '{user_id_column}', skipping")
                    continue

                # Build user properties from configured columns
                user_properties = {}
                for source_col, target_prop in property_columns.items():
                    value = row.get(source_col)
                    if value is not None:
                        # Try to parse JSON if it looks like JSON
                        if isinstance(value, str) and (value.startswith('{') or value.startswith('[')):
                            try:
                                user_properties[target_prop] = json.loads(value)
                            except json.JSONDecodeError:
                                user_properties[target_prop] = value
                        else:
                            # Convert numeric strings if possible
                            if isinstance(value, str):
                                try:
                                    # Try float first (covers both int and float)
                                    if '.' in value:
                                        user_properties[target_prop] = float(value)
                                    else:
                                        user_properties[target_prop] = int(value)
                                except ValueError:
                                    user_properties[target_prop] = value
                            else:
                                user_properties[target_prop] = value

                # Create identification object
                identification = {
                    "user_id": user_id,
                    "user_properties": {
                        "$set": user_properties
                    }
                }

                identifications.append(identification)

                # Send in batches of 2000 (Amplitude limit)
                if len(identifications) >= 2000:
                    logger.info(f"Sending batch of {len(identifications)} user properties to Amplitude...")
                    try:
                        result = driver.update_user_properties(identifications)
                        logger.info(f"✓ Batch successful: {result}")
                    except Exception as e:
                        logger.error(f"✗ Batch failed: {e}")
                        # Continue with next batch

                    identifications = []
                    time.sleep(0.5)  # Small delay between batches

        # Send remaining identifications
        if identifications:
            logger.info(f"Sending final batch of {len(identifications)} user properties to Amplitude...")
            try:
                result = driver.update_user_properties(identifications)
                logger.info(f"✓ Final batch successful: {result}")
            except Exception as e:
                logger.error(f"✗ Final batch failed: {e}")

        logger.info(f"✓ Processed {row_count} rows from input table")

    except Exception as e:
        logger.error(f"Failed to read input table: {e}")
        raise
    finally:
        driver.close()

    return row_count


def main():
    """Main entry point for Keboola component"""
    try:
        # Initialize Keboola Common Interface
        ci = CommonInterface()
        logger.info("✓ Keboola CommonInterface initialized")

        # Get configuration
        parameters = ci.configuration.parameters

        # Determine mode: read, write, or both
        read_enabled = 'start_date' in parameters and 'end_date' in parameters
        write_enabled = len(ci.get_input_tables_definitions()) > 0 and 'property_columns' in parameters

        if not read_enabled and not write_enabled:
            logger.error("No valid configuration found. Set start_date/end_date for read mode or input table with property_columns for write mode.")
            raise ValueError("Invalid configuration")

        api_key = parameters.get('#AMPLITUDE_API_KEY')
        if not api_key:
            logger.error("Missing required parameter: #AMPLITUDE_API_KEY")
            raise ValueError("Missing #AMPLITUDE_API_KEY")

        # READ MODE: Export events from Amplitude
        event_count = 0
        if read_enabled:
            logger.info("READ MODE: Exporting events from Amplitude")

            # Get required parameters for read
            required_params = ['#AMPLITUDE_SECRET_KEY', 'start_date', 'end_date']
            try:
                ci.validate_configuration_parameters(required_params)
            except ValueError as e:
                logger.error(f"Configuration validation failed for read mode: {e}")
                raise

            # Extract read configuration
            secret_key = parameters.get('#AMPLITUDE_SECRET_KEY')
            start_date = parameters.get('start_date')
            end_date = parameters.get('end_date')
            output_table = parameters.get('output_table', 'out.c-amplitude.events')

            logger.info(f"Configuration loaded:")
            logger.info(f"  - Start date: {start_date}")
            logger.info(f"  - End date: {end_date}")
            logger.info(f"  - Output table: {output_table}")

            # Export events
            event_count = export_amplitude_events(
                ci,
                api_key,
                secret_key,
                start_date,
                end_date,
                output_table
            )

            # Update state for incremental runs
            update_state(ci, end_date, event_count)
            logger.info(f"✓ Exported {event_count} events from Amplitude")

        # WRITE MODE: Update user properties in Amplitude
        write_count = 0
        if write_enabled:
            logger.info("WRITE MODE: Updating user properties in Amplitude")

            logger.info(f"Configuration loaded:")
            logger.info(f"  - User ID column: {parameters.get('user_id_column', 'user_id')}")
            logger.info(f"  - Property columns: {parameters.get('property_columns', {})}")

            write_count = write_user_properties_from_table(ci, api_key)
            logger.info(f"✓ Updated {write_count} user properties in Amplitude")

        logger.info(f"✓ Component execution completed successfully")
        if read_enabled:
            logger.info(f"  - Read: {event_count} events exported")
        if write_enabled:
            logger.info(f"  - Write: {write_count} user properties updated")

        return 0

    except Exception as e:
        logger.exception(f"Component execution failed: {e}")
        exit(1)


if __name__ == '__main__':
    main()
