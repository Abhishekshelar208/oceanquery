"""
Knowledge Manager for OceanQuery RAG system.

Handles ingestion, preprocessing, and management of oceanographic knowledge.
"""

import logging
import json
from typing import Dict, List, Any, Optional, Set
from pathlib import Path
from datetime import datetime

from .vector_store import VectorStoreService

logger = logging.getLogger(__name__)


class KnowledgeManager:
    """Manages oceanographic knowledge base for RAG system."""
    
    def __init__(self, vector_store: VectorStoreService):
        """
        Initialize knowledge manager.
        
        Args:
            vector_store: Vector store service instance
        """
        self.vector_store = vector_store
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # Track loaded knowledge sources
        self.loaded_sources = set()
        
    def load_oceanographic_knowledge(self) -> Dict[str, bool]:
        """Load comprehensive oceanographic knowledge into the vector store."""
        
        knowledge_data = self._get_oceanographic_knowledge_data()
        results = self.vector_store.bulk_add_knowledge(knowledge_data)
        
        # Track successfully loaded sources
        for collection_name, success in results.items():
            if success:
                self.loaded_sources.add(collection_name)
                
        self.logger.info(f"Loaded knowledge into {len([r for r in results.values() if r])} collections")
        return results
    
    def _get_oceanographic_knowledge_data(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get structured oceanographic knowledge data for all collections."""
        
        return {
            "oceanography": self._get_general_oceanography_knowledge(),
            "argo": self._get_argo_knowledge(), 
            "measurements": self._get_measurement_knowledge(),
            "analysis": self._get_analysis_knowledge(),
            "examples": self._get_query_examples(),
            "bgc": self._get_bgc_knowledge()
        }
    
    def _get_general_oceanography_knowledge(self) -> List[Dict[str, Any]]:
        """Get general oceanographic concepts and terminology."""
        
        knowledge_items = [
            {
                "content": "Temperature is a fundamental property of seawater that affects density, ocean circulation, and marine life distribution. Ocean temperature varies with depth, latitude, and season. Surface temperatures typically range from -2°C to 35°C globally.",
                "metadata": {"topic": "temperature", "category": "basic_concepts", "importance": "high"}
            },
            {
                "content": "Salinity measures the concentration of dissolved salts in seawater, typically expressed in practical salinity units (PSU) or parts per thousand (ppt). Global ocean salinity ranges from about 32-37 PSU, with an average of 35 PSU.",
                "metadata": {"topic": "salinity", "category": "basic_concepts", "importance": "high"}
            },
            {
                "content": "The thermocline is a distinct layer in the ocean where temperature changes rapidly with depth. It separates the warm, well-mixed surface layer from the cold, deep waters below. The thermocline depth varies seasonally and geographically.",
                "metadata": {"topic": "thermocline", "category": "water_column_structure", "importance": "medium"}
            },
            {
                "content": "Ocean density is primarily controlled by temperature and salinity. Cold, salty water is denser than warm, fresh water. Density differences drive thermohaline circulation, the global conveyor belt of ocean currents.",
                "metadata": {"topic": "density", "category": "physical_properties", "importance": "high"}
            },
            {
                "content": "The mixed layer is the uppermost layer of the ocean where temperature, salinity, and density are relatively uniform due to wind mixing and surface cooling/heating. It typically extends from 10-200 meters depth.",
                "metadata": {"topic": "mixed_layer", "category": "water_column_structure", "importance": "medium"}
            },
            {
                "content": "Chlorophyll-a is the primary photosynthetic pigment in marine phytoplankton. Chlorophyll concentrations indicate phytoplankton biomass and ocean productivity. Values typically range from 0.01-10 mg/m³ in open ocean to coastal waters.",
                "metadata": {"topic": "chlorophyll", "category": "biological_properties", "importance": "medium"}
            },
            {
                "content": "Dissolved oxygen levels in seawater indicate biological activity and water mass properties. High oxygen suggests recent contact with atmosphere or photosynthesis, while low oxygen indicates respiration or poor ventilation.",
                "metadata": {"topic": "oxygen", "category": "chemical_properties", "importance": "medium"}
            },
            {
                "content": "The pycnocline is a layer of rapidly changing water density in the ocean, primarily caused by temperature and salinity gradients. It acts as a barrier to vertical mixing and is crucial for ocean stratification.",
                "metadata": {"topic": "pycnocline", "category": "water_column_structure", "importance": "medium"}
            },
            {
                "content": "Upwelling is the process where cold, nutrient-rich deep water rises to the surface, typically along coastlines or at the equator. This process supports high marine productivity and affects regional climate.",
                "metadata": {"topic": "upwelling", "category": "circulation", "importance": "medium"}
            },
            {
                "content": "El Niño and La Niña are climate phenomena involving changes in Pacific Ocean temperatures that affect global weather patterns. El Niño brings warm water to the eastern Pacific, while La Niña brings cooler conditions.",
                "metadata": {"topic": "enso", "category": "climate_phenomena", "importance": "high"}
            }
        ]
        
        return knowledge_items
    
    def _get_argo_knowledge(self) -> List[Dict[str, Any]]:
        """Get ARGO float system knowledge."""
        
        knowledge_items = [
            {
                "content": "ARGO floats are autonomous robotic instruments that drift with ocean currents and measure temperature, salinity, and pressure profiles. They dive to 2000m depth every 10 days, then surface to transmit data via satellite.",
                "metadata": {"topic": "argo_basics", "category": "instrumentation", "importance": "high"}
            },
            {
                "content": "The ARGO array consists of approximately 4000 active floats globally, providing real-time ocean observations. Each float has a mission duration of 3-5 years and completes about 150 dive cycles.",
                "metadata": {"topic": "argo_network", "category": "global_coverage", "importance": "high"}
            },
            {
                "content": "ARGO floats measure conductivity (for salinity calculation), temperature, and pressure using high-precision sensors. Modern floats also carry additional sensors for oxygen, pH, nitrate, and other biogeochemical parameters.",
                "metadata": {"topic": "argo_sensors", "category": "measurements", "importance": "medium"}
            },
            {
                "content": "ARGO data undergoes rigorous quality control including real-time and delayed-mode processing. Delayed-mode processing includes calibration adjustments and additional quality checks, typically completed within 6-12 months.",
                "metadata": {"topic": "argo_quality_control", "category": "data_processing", "importance": "medium"}
            },
            {
                "content": "Float trajectories are influenced by ocean currents at different depths during their parking phase (typically 1000m depth). This provides information about subsurface current patterns and circulation.",
                "metadata": {"topic": "argo_trajectories", "category": "circulation", "importance": "medium"}
            },
            {
                "content": "Core ARGO floats measure temperature and salinity from 2000m to surface. Biogeochemical ARGO (BGC-ARGO) floats add sensors for dissolved oxygen, chlorophyll, particle backscatter, and other parameters.",
                "metadata": {"topic": "argo_types", "category": "instrumentation", "importance": "medium"}
            },
            {
                "content": "ARGO data is freely available in near real-time (within 24 hours) and delayed-mode (quality-controlled) versions. Data formats include NetCDF files with standardized metadata and quality flags.",
                "metadata": {"topic": "argo_data_access", "category": "data_management", "importance": "low"}
            },
            {
                "content": "Profile quality is indicated by ARGO quality flags: 1=good, 2=probably good, 3=probably bad, 4=bad, 5=value changed, 8=estimated, 9=missing. Only flags 1 and 2 should be used for scientific analysis.",
                "metadata": {"topic": "argo_quality_flags", "category": "data_quality", "importance": "medium"}
            }
        ]
        
        return knowledge_items
    
    def _get_measurement_knowledge(self) -> List[Dict[str, Any]]:
        """Get ocean measurement explanations."""
        
        knowledge_items = [
            {
                "content": "Practical Salinity Units (PSU) are the standard unit for measuring seawater salinity. PSU is dimensionless and based on conductivity ratios relative to a standard seawater sample. It closely approximates parts per thousand (ppt).",
                "metadata": {"topic": "salinity_units", "category": "units", "importance": "medium"}
            },
            {
                "content": "Potential temperature is temperature adjusted for the effect of pressure. It represents what the temperature would be if a water parcel were moved adiabatically to the surface, useful for comparing water masses at different depths.",
                "metadata": {"topic": "potential_temperature", "category": "derived_parameters", "importance": "medium"}
            },
            {
                "content": "Pressure in the ocean is measured in decibars (dbar), where 1 dbar ≈ 1 meter depth. Surface pressure is ~10 dbar, and pressure increases by ~1 dbar per meter of depth due to the weight of overlying water.",
                "metadata": {"topic": "pressure_depth", "category": "units", "importance": "low"}
            },
            {
                "content": "Sigma-t (σt) is potential density anomaly referenced to the surface (0 dbar). It's calculated from temperature and salinity and indicates water mass characteristics. Typical values range from 20-28 kg/m³.",
                "metadata": {"topic": "sigma_t", "category": "derived_parameters", "importance": "medium"}
            },
            {
                "content": "Buoyancy frequency (N²) quantifies ocean stratification strength. High N² indicates strong stratification that inhibits vertical mixing, while low N² suggests weak stratification allowing easier mixing between layers.",
                "metadata": {"topic": "buoyancy_frequency", "category": "derived_parameters", "importance": "low"}
            },
            {
                "content": "Mixed Layer Depth (MLD) is determined by temperature or density criteria, typically a 0.2°C temperature difference or 0.03 kg/m³ density difference from the surface. It varies seasonally and affects air-sea exchange.",
                "metadata": {"topic": "mixed_layer_depth", "category": "derived_parameters", "importance": "medium"}
            },
            {
                "content": "Oxygen saturation percentage indicates how much dissolved oxygen is present relative to equilibrium with the atmosphere at the same temperature and salinity. Values >100% suggest supersaturation from photosynthesis.",
                "metadata": {"topic": "oxygen_saturation", "category": "chemical_measurements", "importance": "low"}
            }
        ]
        
        return knowledge_items
    
    def _get_analysis_knowledge(self) -> List[Dict[str, Any]]:
        """Get data analysis methods and interpretations."""
        
        knowledge_items = [
            {
                "content": "Time series analysis of ocean data reveals seasonal cycles, long-term trends, and anomalies. Seasonal patterns in temperature show surface warming in summer and cooling in winter, with deeper layers showing delayed responses.",
                "metadata": {"topic": "time_series_analysis", "category": "analysis_methods", "importance": "medium"}
            },
            {
                "content": "Temperature-Salinity (T-S) diagrams are powerful tools for identifying water masses and analyzing mixing processes. Different water masses occupy characteristic regions in T-S space based on their formation conditions.",
                "metadata": {"topic": "ts_diagrams", "category": "analysis_methods", "importance": "high"}
            },
            {
                "content": "Vertical profiles show how ocean properties change with depth. Typical patterns include warm surface mixed layers, thermoclines, and cold deep waters. Anomalous profiles may indicate upwelling, eddies, or other processes.",
                "metadata": {"topic": "vertical_profiles", "category": "analysis_methods", "importance": "high"}
            },
            {
                "content": "Spatial averaging helps identify regional patterns and reduces noise in ocean data. Averaging can be done over boxes, along transects, or using weighted methods that account for data density and quality.",
                "metadata": {"topic": "spatial_averaging", "category": "analysis_methods", "importance": "medium"}
            },
            {
                "content": "Anomaly analysis compares current conditions to long-term averages or climatologies. Positive anomalies indicate warmer/saltier conditions than normal, while negative anomalies show cooler/fresher conditions.",
                "metadata": {"topic": "anomaly_analysis", "category": "analysis_methods", "importance": "medium"}
            },
            {
                "content": "Quality control is essential for ocean data analysis. This includes checking for instrument drift, spikes, impossible values, and comparing with nearby measurements. ARGO data includes quality flags to guide usage.",
                "metadata": {"topic": "quality_control", "category": "data_processing", "importance": "high"}
            },
            {
                "content": "Interpolation methods fill gaps in ocean data for analysis and visualization. Common methods include linear, cubic spline, and objective analysis. Choice depends on data density, expected variability, and application requirements.",
                "metadata": {"topic": "interpolation", "category": "data_processing", "importance": "low"}
            }
        ]
        
        return knowledge_items
    
    def _get_query_examples(self) -> List[Dict[str, Any]]:
        """Get example queries and their explanations."""
        
        knowledge_items = [
            {
                "content": "Query: 'Show temperature profiles in the North Atlantic' - This asks for vertical temperature data from a specific geographic region. Analysis should include depth ranges, seasonal patterns, and comparison with climatology.",
                "metadata": {"topic": "temperature_profiles", "category": "query_examples", "importance": "high"}
            },
            {
                "content": "Query: 'What's the mixed layer depth trend in the Pacific?' - This requests time series analysis of mixed layer depth evolution. Consider seasonal cycles, interannual variability, and long-term climate change effects.",
                "metadata": {"topic": "mixed_layer_trends", "category": "query_examples", "importance": "medium"}
            },
            {
                "content": "Query: 'Compare salinity between El Niño and La Niña years' - This asks for composite analysis during different ENSO phases. Focus on Pacific Ocean changes and their propagation to other basins.",
                "metadata": {"topic": "enso_comparison", "category": "query_examples", "importance": "medium"}
            },
            {
                "content": "Query: 'Show recent temperature anomalies globally' - This requests current conditions compared to historical averages. Include surface and subsurface patterns, and relate to climate indices if relevant.",
                "metadata": {"topic": "temperature_anomalies", "category": "query_examples", "importance": "high"}
            },
            {
                "content": "Query: 'What causes the thermocline to vary seasonally?' - This asks for process understanding. Explain surface heating/cooling, wind mixing, and convection effects on water column structure.",
                "metadata": {"topic": "seasonal_thermocline", "category": "query_examples", "importance": "medium"}
            },
            {
                "content": "Query: 'Density stratification in the Southern Ocean' - This requests analysis of water column stability. Include mixed layer depths, pycnocline strength, and implications for mixing and circulation.",
                "metadata": {"topic": "density_stratification", "category": "query_examples", "importance": "medium"}
            }
        ]
        
        return knowledge_items
    
    def _get_bgc_knowledge(self) -> List[Dict[str, Any]]:
        """Get Bio-Geo-Chemical (BGC) knowledge for competition compliance."""
        
        knowledge_items = [
            {
                "content": "Bio-Geo-Chemical (BGC) ARGO floats extend traditional temperature-salinity measurements by adding sensors for dissolved oxygen, pH, nitrate, chlorophyll-a, and particle backscattering. These parameters provide insights into ocean productivity, carbon cycle, and ecosystem health.",
                "metadata": {"topic": "bgc_floats", "category": "instrumentation", "importance": "high"}
            },
            {
                "content": "Chlorophyll-a concentration is measured using fluorescence sensors on BGC floats. It indicates phytoplankton biomass and primary productivity. Values range from <0.1 mg/m³ in oligotrophic (nutrient-poor) regions to >10 mg/m³ in eutrophic (nutrient-rich) coastal waters.",
                "metadata": {"topic": "chlorophyll_a", "category": "biological_parameters", "importance": "high"}
            },
            {
                "content": "Ocean pH measurements by BGC floats detect ocean acidification caused by atmospheric CO2 absorption. Typical seawater pH ranges from 7.8-8.2. Decreasing pH threatens marine organisms with calcium carbonate shells, including corals, mollusks, and some plankton.",
                "metadata": {"topic": "ocean_ph", "category": "chemical_parameters", "importance": "high"}
            },
            {
                "content": "Nitrate is measured by BGC floats using UV spectrophotometry. As a key nutrient limiting phytoplankton growth, nitrate concentrations vary from near-zero in surface waters to 40+ μmol/kg in deep waters. Upwelling brings nitrate-rich water to the surface, supporting marine productivity.",
                "metadata": {"topic": "nitrate_measurements", "category": "chemical_parameters", "importance": "medium"}
            },
            {
                "content": "Dissolved oxygen is measured by BGC floats using optical sensors. Oxygen levels indicate biological activity and water mass ventilation. High oxygen suggests recent atmospheric contact or photosynthesis, while low oxygen indicates respiration or poor ventilation. Oxygen minimum zones (OMZs) have <20 μmol/kg.",
                "metadata": {"topic": "dissolved_oxygen", "category": "chemical_parameters", "importance": "high"}
            },
            {
                "content": "Particle backscattering measured by BGC floats provides information about particle concentration and size distribution in seawater. This includes marine snow, phytoplankton, and detritus. Multiple wavelengths help distinguish particle types and estimate biogeochemical processes.",
                "metadata": {"topic": "backscattering", "category": "optical_parameters", "importance": "medium"}
            },
            {
                "content": "BGC floats enable study of the biological carbon pump - the process where marine organisms transport carbon from surface to deep ocean through photosynthesis, death, and sinking. This process affects atmospheric CO2 levels and global climate regulation.",
                "metadata": {"topic": "carbon_pump", "category": "biogeochemical_processes", "importance": "high"}
            },
            {
                "content": "Oxygen minimum zones (OMZs) are detected by BGC floats as regions with extremely low dissolved oxygen (<20 μmol/kg). These zones, expanding due to climate change, create dead zones where most marine life cannot survive, affecting ocean biodiversity and fisheries.",
                "metadata": {"topic": "oxygen_minimum_zones", "category": "ecosystem_health", "importance": "medium"}
            },
            {
                "content": "BGC float data helps validate satellite ocean color measurements and improves global estimates of marine primary productivity. The combination of in-situ BGC measurements with satellite observations provides comprehensive monitoring of ocean ecosystem changes.",
                "metadata": {"topic": "satellite_validation", "category": "remote_sensing", "importance": "medium"}
            },
            {
                "content": "Seasonal phytoplankton blooms are captured by BGC float chlorophyll measurements, revealing bloom timing, magnitude, and spatial extent. Spring blooms in temperate oceans and monsoon-driven blooms in tropical regions are key features of marine ecosystem dynamics.",
                "metadata": {"topic": "phytoplankton_blooms", "category": "ecosystem_dynamics", "importance": "medium"}
            },
            {
                "content": "BGC quality control procedures ensure data reliability through real-time range checks, spike detection, and comparison with climatology. Delayed-mode processing includes sensor calibration drift correction and cross-calibration with ship-based reference measurements.",
                "metadata": {"topic": "bgc_quality_control", "category": "data_quality", "importance": "low"}
            },
            {
                "content": "Primary productivity is the rate at which phytoplankton convert inorganic carbon into organic matter through photosynthesis. BGC floats measure chlorophyll and oxygen to estimate productivity rates, crucial for understanding marine food webs and carbon cycling.",
                "metadata": {"topic": "primary_productivity", "category": "biological_processes", "importance": "high"}
            },
            {
                "content": "Deep chlorophyll maximum (DCM) is a subsurface layer where chlorophyll concentrations peak, typically found at the base of the euphotic zone. BGC floats reveal DCM depth, intensity, and seasonal variations, important for understanding deep ocean productivity.",
                "metadata": {"topic": "deep_chlorophyll_maximum", "category": "biological_features", "importance": "medium"}
            },
            {
                "content": "Marine carbonate chemistry, including pH, total alkalinity, and dissolved inorganic carbon, is altered by ocean acidification. BGC floats measuring pH help track acidification impacts on shell-forming organisms and ecosystem changes.",
                "metadata": {"topic": "carbonate_chemistry", "category": "ocean_acidification", "importance": "high"}
            },
            {
                "content": "Nutrient cycling in the ocean involves uptake by phytoplankton in surface waters and regeneration at depth through decomposition. BGC floats measuring nitrate reveal nutrient distribution patterns and seasonal cycles that control marine productivity.",
                "metadata": {"topic": "nutrient_cycling", "category": "biogeochemical_processes", "importance": "medium"}
            }
        ]
        
        return knowledge_items
    
    def add_custom_knowledge(
        self, 
        collection_name: str, 
        documents: List[str], 
        metadata_list: Optional[List[Dict[str, Any]]] = None
    ) -> bool:
        """Add custom knowledge to a specific collection."""
        
        if metadata_list is None:
            metadata_list = [{"source": "custom", "added": datetime.now().isoformat()} 
                           for _ in documents]
        
        success = self.vector_store.add_documents(
            collection_name=collection_name,
            documents=documents,
            metadatas=metadata_list
        )
        
        if success:
            self.loaded_sources.add(f"custom_{collection_name}")
            self.logger.info(f"Added {len(documents)} custom documents to '{collection_name}'")
        
        return success
    
    def get_knowledge_stats(self) -> Dict[str, Any]:
        """Get comprehensive knowledge base statistics."""
        
        collection_stats = self.vector_store.get_collection_stats()
        
        total_documents = sum(
            stats.get('document_count', 0) 
            for stats in collection_stats.values()
        )
        
        return {
            "total_documents": total_documents,
            "collections": collection_stats,
            "loaded_sources": list(self.loaded_sources),
            "last_updated": datetime.now().isoformat()
        }
    
    def search_knowledge(
        self, 
        query: str, 
        collections: Optional[List[str]] = None,
        max_results: int = 10,
        min_relevance: float = 0.7
    ) -> List[Dict[str, Any]]:
        """Search the knowledge base for relevant information."""
        
        results = self.vector_store.search_similar(
            query=query,
            collection_names=collections,
            n_results=max_results,
            min_relevance_score=min_relevance
        )
        
        # Add knowledge context to results
        for result in results:
            result['knowledge_type'] = result['collection']
            result['relevance_score'] = result['similarity_score']
        
        return results
    
    def export_knowledge_summary(self) -> Dict[str, Any]:
        """Export a summary of the current knowledge base."""
        
        stats = self.get_knowledge_stats()
        
        # Get sample documents from each collection
        samples = {}
        for collection_name in self.vector_store.collections.keys():
            try:
                collection = self.vector_store.collections[collection_name]
                # Get a few sample documents
                results = collection.peek(limit=3)
                if results and results.get('documents'):
                    samples[collection_name] = [
                        doc[:100] + "..." if len(doc) > 100 else doc
                        for doc in results['documents']
                    ]
            except Exception as e:
                self.logger.error(f"Error getting samples from {collection_name}: {e}")
                samples[collection_name] = []
        
        return {
            "statistics": stats,
            "sample_documents": samples,
            "export_timestamp": datetime.now().isoformat()
        }


def create_knowledge_manager(vector_store: VectorStoreService) -> KnowledgeManager:
    """Factory function to create knowledge manager."""
    return KnowledgeManager(vector_store)