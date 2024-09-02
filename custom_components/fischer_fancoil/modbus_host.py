"""Modbus host for Fischer Fancoil."""

import asyncio

from pymodbus.client import AsyncModbusTcpClient


class ModbusHost:
    """Modbus host for Fischer Fancoil."""

    def __init__(self, host, port) -> None:
        """Initialize the modbus host."""
        self._host = host
        self._port = port
        self._client = AsyncModbusTcpClient(host=host, port=port)
        self._lock = asyncio.Lock()
        self._subscriber_count = 0

    async def async_connect(self):
        """Connect to the modbus host."""
        if not self._client.connected:
            await self._client.connect()

    async def async_disconnect(self):
        """Disconnect from the modbus host."""
        if self._client.connected:
            await self._client.close()

    def add_subscriber(self):
        """Add a subscriber."""
        self._subscriber_count += 1

    def get_subscriber_count(self):
        """Get the subscriber count."""
        return self._subscriber_count

    def remove_subscriber(self):
        """Remove a subscriber."""
        self._subscriber_count -= 1
        if self._subscriber_count == 0:
            task = asyncio.create_task(self.async_disconnect())
            # TODO: destroy host instance if no subscribers

    async def async_read_holding_registers(self, unit_id, address, count):
        """Read holding registers."""
        async with self._lock:
            await self.async_connect()
            result = await self._client.read_holding_registers(address, count, unit_id)
            if not result.isError():
                return result.registers
            return None

    async def async_read_input_registers(self, unit_id, address, count):
        """Read input registers."""
        async with self._lock:
            await self.async_connect()
            result = await self._client.read_input_registers(address, count, unit_id)
            if not result.isError():
                return result.registers
            return None

    async def async_read_coil(self, unit_id, address):
        """Read coils."""
        async with self._lock:
            await self.async_connect()
            result = await self._client.read_coils(address, 1, unit_id)
            if not result.isError():
                return result.bits[0]
            return None

    async def async_read_coils(self, unit_id, address, count):
        """Read coils."""
        async with self._lock:
            await self.async_connect()
            result = await self._client.read_coils(address, count, unit_id)
            if not result.isError():
                return result.bits
            return None

    async def async_write_register(self, unit_id, address, value):
        """Write a single register."""
        async with self._lock:
            await self.async_connect()
            result = await self._client.write_register(address, value, unit_id)
            return not result.isError()
