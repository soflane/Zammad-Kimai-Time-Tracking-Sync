import pytest
from unittest.mock import AsyncMock, patch
from datetime import datetime, timedelta
import httpx

from app.services.kimai_metadata import KimaiMetadataService
from app.connectors.base import TimeEntryNormalized

@pytest.mark.asyncio
class TestKimaiMetadataService:
    @pytest.fixture
    def service(self):
        service = KimaiMetadataService("https://example.com", "fake-token")
        yield service
        service.close()

    @pytest.mark.asyncio
    async def test_get_customer_name_caches(self, service):
        with patch('httpx.AsyncClient.get') as mock_get:
            mock_response = AsyncMock()
            mock_response.raise_for_status.return_value = None
            mock_response.json.return_value = {"name": "Test Customer"}
            mock_get.return_value = mock_response

            # First call: API
            name1 = await service.get_customer_name(1)
            assert name1 == "Test Customer"
            mock_get.assert_called_once()

            # Second call: cache
            name2 = await service.get_customer_name(1)
            assert name2 == "Test Customer"
            mock_get.assert_called_once()  # Still once

    @pytest.mark.asyncio
    async def test_get_customer_name_ttl_expires(self, service):
        with patch('httpx.AsyncClient.get') as mock_get:
            mock_response = AsyncMock()
            mock_response.raise_for_status.return_value = None
            mock_response.json.return_value = {"name": "Test Customer"}
            mock_get.return_value = mock_response

            # First call
            name1 = await service.get_customer_name(1)
            assert name1 == "Test Customer"

            # Mock time advance > TTL
            with patch('time.time', return_value=datetime.now().timestamp() + 601):  # > 600s
                # Second call: API again
                name2 = await service.get_customer_name(1)
                assert name2 == "Test Customer"
                mock_get.assert_called_twice()

    @pytest.mark.asyncio
    async def test_get_customer_name_error_returns_none(self, service):
        with patch('httpx.AsyncClient.get') as mock_get:
            mock_response = AsyncMock()
            mock_response.raise_for_status.side_effect = httpx.HTTPStatusError("Not Found", response=mock_response)
            mock_get.return_value = mock_response

            name = await service.get_customer_name(1)
            assert name is None

    @pytest.mark.asyncio
    async def test_enrich_normalized_entry_sets_names(self, service):
        with patch.object(service, 'get_customer_name', new_callable=AsyncMock) as mock_customer, \
             patch.object(service, 'get_project_name', new_callable=AsyncMock) as mock_project, \
             patch.object(service, 'get_activity_name', new_callable=AsyncMock) as mock_activity:

            mock_customer.return_value = "Customer Inc"
            mock_project.return_value = "Project X"
            mock_activity.return_value = "Activity Y"

            entry = TimeEntryNormalized(
                source_id="test",
                source="zammad",
                description="test",
                duration_sec=3600,
                entry_date="2025-10-29",
                customer_id=1,
                project_id=2,
                activity_id=3
            )

            enriched = await service.enrich_normalized_entry(entry)

            assert enriched.customer_name == "Customer Inc"
            assert enriched.project_name == "Project X"
            assert enriched.activity_name == "Activity Y"
            mock_customer.assert_called_with(1)
            mock_project.assert_called_with(2)
            mock_activity.assert_called_with(3)

    @pytest.mark.asyncio
    async def test_enrich_normalized_entry_no_ids_skips(self, service):
        with patch.object(service, 'get_customer_name', new_callable=AsyncMock) as mock_customer:
            entry = TimeEntryNormalized(
                source_id="test",
                source="zammad",
                description="test",
                duration_sec=3600,
                entry_date="2025-10-29"
            )

            enriched = await service.enrich_normalized_entry(entry)

            assert enriched.customer_name is None
            assert enriched.project_name is None
            assert enriched.activity_name is None
            mock_customer.assert_not_called()

    @pytest.mark.asyncio
    async def test_enrich_normalized_entry_non_zammad_skips(self, service):
        with patch.object(service, 'get_customer_name', new_callable=AsyncMock) as mock_customer:
            entry = TimeEntryNormalized(
                source_id="test",
                source="kimai",
                description="test",
                duration_sec=3600,
                entry_date="2025-10-29",
                customer_id=1
            )

            enriched = await service.enrich_normalized_entry(entry)

            assert enriched.customer_name is None
            mock_customer.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_project_name_caches(self, service):
        with patch('httpx.AsyncClient.get') as mock_get:
            mock_response = AsyncMock()
            mock_response.raise_for_status.return_value = None
            mock_response.json.return_value = {"name": "Test Project"}
            mock_get.return_value = mock_response

            name1 = await service.get_project_name(2)
            assert name1 == "Test Project"
            mock_get.assert_called_once()

            name2 = await service.get_project_name(2)
            assert name2 == "Test Project"
            mock_get.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_activity_name_caches(self, service):
        with patch('httpx.AsyncClient.get') as mock_get:
            mock_response = AsyncMock()
            mock_response.raise_for_status.return_value = None
            mock_response.json.return_value = {"name": "Test Activity"}
            mock_get.return_value = mock_response

            name1 = await service.get_activity_name(3)
            assert name1 == "Test Activity"
            mock_get.assert_called_once()

            name2 = await service.get_activity_name(3)
            assert name2 == "Test Activity"
            mock_get.assert_called_once()

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
