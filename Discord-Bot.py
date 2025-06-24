import discord
import json
import math
import io
from collections import defaultdict
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.ticker import FuncFormatter, MaxNLocator
from datetime import datetime, timezone, timedelta
import numpy as np
import platform
import datetime
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.ticker import FuncFormatter
import pandas as pd
from pandas import json_normalize
from discord import app_commands, Interaction, ButtonStyle
from discord import app_commands
from discord.ext import commands
import requests
from dotenv import load_dotenv
from bs4 import BeautifulSoup
from discord.ui import View, Modal, TextInput, button
from discord.ui import Button, View
import random
import os
from io import BytesIO
import json
from datetime import datetime
import re
from datetime import timezone
import io
from discord import File
from io import StringIO
import matplotlib.pyplot as plt
import asyncio
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import discord
from discord import app_commands, Interaction
import asyncio
from matplotlib.ticker import MaxNLocator, FuncFormatter
from datetime import datetime, timedelta, timezone
import matplotlib.dates as mdates
from discord.ext import tasks
from datetime import datetime, date
from datetime import datetime, timezone
from collections import defaultdict

cached_users = {}
cached_sheet_data = []

load_dotenv("cred.env")
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="/", intents=intents)
bot_key = os.getenv("Key")
API_KEY = os.getenv("API_KEY")
YT_Key = os.getenv("YT_Key")
commandscalled = {"_global": 0}
snapshots_file = "snapshots.json"
money_snapshots = []

if os.path.exists(snapshots_file):
    with open(snapshots_file, "r") as f:
        money_snapshots = json.load(f)

UNIT_PRICES = {
    "soldiers": 5,
    "tanks": 60,
    "aircraft": 4000,
    "ships": 50000,
    "missiles": 150000,
    "nuclear": 1750000
}

BUILD_CATEGORIES = {
    "Power Plants": [
        "coal_power", "oil_power", "nuclear_power", "wind_power"
    ],
    "Raw Resources": [
        "coal_mine", "iron_mine", "lead_mine", "farm", "oil_well", "uranium_mine", "bauxite_mine"
    ],
    "Manufacturing": [
        "oil_refinery", "steel_mill", "aluminum_refinery", "munitions_factory"
    ],
    "Civil": [
        "police_station", "hospital", "recycling_center", "subway"
    ],
    "Commerce": [
        "supermarket", "bank", "shopping_mall", "stadium"
    ],
    "Military": [
        "barracks", "factory", "hangar", "drydock"
    ]
}

BUILD_KEYS = [k for v in BUILD_CATEGORIES.values() for k in v]

PROJECT_KEYS = [
    "iron_works", "bauxite_works", "arms_stockpile", "emergency_gasoline_reserve",
    "mass_irrigation", "international_trade_center", "missile_launch_pad",
    "nuclear_research_facility", "iron_dome", "vital_defense_system",
    "central_intelligence_agency", "center_for_civil_engineering", "propaganda_bureau",
    "uranium_enrichment_program", "urban_planning", "advanced_urban_planning",
    "space_program", "spy_satellite", "moon_landing", "pirate_economy",
    "recycling_initiative", "telecommunications_satellite", "green_technologies",
    "arable_land_agency", "clinical_research_center", "specialized_police_training_program",
    "advanced_engineering_corps", "government_support_agency",
    "research_and_development_center", "metropolitan_planning", "military_salvage",
    "fallout_shelter", "activity_center", "bureau_of_domestic_affairs",
    "advanced_pirate_economy", "mars_landing", "surveillance_network",
    "guiding_satellite", "nuclear_launch_facility", "military_research_center",
    "military_doctrine"
]

class NationInfoView(discord.ui.View):
    def __init__(self, nation_id, original_embed):
        super().__init__(timeout=120)
        self.nation_id = nation_id
        self.original_embed = original_embed

    async def fetch_and_group(self, keys):
        df = graphql_cities(self.nation_id)
        cities = extract_cities_from_df(df)
        if cities is None:
            return None, "Failed to fetch city data."
        
        groups = defaultdict(list)
        for city in cities:
            present = tuple(
                (key, city.get(key))
                for key in keys
                if city.get(key) not in (0, None, False, "")
            )
            groups[present].append(f"{city.get('name')} ({city.get('id')})")

        return groups, None

    async def show_grouped(self, interaction: discord.Interaction, keys, title):
        groups, err = await self.fetch_and_group(keys)
        if err:
            await interaction.response.send_message(err, ephemeral=True)
            return

        description = ""
        for buildings, city_names in groups.items():
            if not buildings:
                continue
            building_str = ", ".join(
                f"{k.replace('_', ' ').title()}: {v}" if not isinstance(v, bool) else f"{k.replace('_', ' ').title()}"
                for k, v in buildings
            )
            description += f"**{building_str}**\nCities: {', '.join(city_names)}\n\n"

        if description == "":
            description = "No cities with those buildings/projects found."

        embed = discord.Embed(title=title, description=description, color=discord.Color.blurple())
        embed.set_footer(text="Data fetched live from Politics & War API")

        # Reset buttons: only show Back + Close after grouping
        self.clear_items()
        self.add_item(BackButton(self.original_embed, self))
        self.add_item(CloseButton())

        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Show Builds", style=discord.ButtonStyle.primary)
    async def builds_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        nation_id = self.nation_id
        df = graphql_cities(nation_id)
        if df is None or df.empty:
            await interaction.response.send_message("❌ Failed to fetch or parse city data.", ephemeral=True)
            return
    
        try:
            nation = df.iloc[0]
            num_cities = nation.get("num_cities", 999999)
            cities = nation.get("cities", [])
    
            grouped = {}
            for city in cities:
                infra = city.get("infrastructure", 0)
                build_signature = tuple((key, city.get(key, 0)) for key in BUILD_KEYS)
                grouped.setdefault(build_signature, []).append((city["name"], infra))
    
            description = ""
            for build, city_list in grouped.items():
                count = len(city_list)
                header = f"🏙️ **{count}/{num_cities} have this build:**\n"
                build_lines = [f"{name} (Infra: {infra})" for name, infra in city_list]
    
                # Organize build details by category
                category_lines = []
                build_dict = dict(build)
                for cat, keys in BUILD_CATEGORIES.items():
                    parts = [f"{k.replace('_', ' ').title()}: {build_dict.get(k, 0)}"
                             for k in keys if k in build_dict and build_dict[k]]
                    if parts:
                        category_lines.append(f"🔹 __{cat}__:\n" + "\n".join(f"• {p}" for p in parts))
    
                build_desc = "\n".join(category_lines)
                block = header + "\n".join(build_lines) + f"\n\n{build_desc}\n\n"
    
                if len(description) + len(block) > 3900:
                    break  # stay within embed limit
                description += block
    
            if not description:
                description = "No valid build data found."
    
            embed = discord.Embed(title="Grouped City Builds", description=description, color=discord.Color.blurple())
            embed.set_footer(text="Data fetched live from Politics & War API")
    
            self.clear_items()
            self.add_item(BackButton(self.original_embed, self))
            self.add_item(CloseButton())
    
            await interaction.response.edit_message(embed=embed, view=self)
    
        except Exception as e:
            await interaction.followup.send(f"❌ Error while formatting builds: {e}", ephemeral=True)

    @discord.ui.button(label="Show Projects", style=discord.ButtonStyle.secondary)
    async def projects_button(self, interaction: discord.Interaction, button: discord.ui.Button):
    
        nation_id = self.nation_id
        df = graphql_cities(nation_id)
    
        if df is None or df.empty:
            await interaction.followup.send("❌ Failed to fetch project data.", ephemeral=True)
            return
    
        try:
            nation = df.iloc[0]
            projects_status = []
    
            for proj in PROJECT_KEYS:
                emoji = "✅" if nation.get(proj, False) else "❌"
                if emoji == "✅":
                    projects_status.append(f"{proj.replace('_', ' ').title()}")
    
            chunks = [projects_status[i:i + 20] for i in range(0, len(projects_status), 20)]
            embed = discord.Embed(
                title="Projects",
                colour=discord.Colour.purple()
            )
            for chunk in chunks:
                embed.add_field(name="Projects", value="\n".join(chunk), inline=False)
    
            self.clear_items()
            self.add_item(BackButton(self.original_embed, self))
            self.add_item(CloseButton())
    
            await interaction.response.edit_message(embed=embed, view=self)
    
        except Exception as e:
            await interaction.followup.send(f"❌ Error while formatting projects: {e}", ephemeral=True)
                
    @discord.ui.button(label="Warchest", style=discord.ButtonStyle.success)
    async def audit_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        nation_id = self.nation_id
    
        try:
            GRAPHQL_URL = f"https://api.politicsandwar.com/graphql?api_key={API_KEY}"
            query = f"""
            {{
              nations(id: [{nation_id}]) {{
                data {{
                  id
                  nation_name
                  num_cities
                  food
                  uranium
                  money
                  gasoline
                  munitions
                  steel
                  aluminum
                }}
              }}
            }}
            """
            response = requests.post(
                GRAPHQL_URL,
                json={"query": query},
                headers={"Content-Type": "application/json"}
            )
    
            data = response.json()["data"]["nations"]["data"]
            if not data:
                await interaction.followup.send("❌ Nation not found.", ephemeral=True)
                return
    
            nation = data[0]
            city_count = int(nation["num_cities"])
    
            requirements = {
                "Money": (city_count * 1_000_000, nation["money"]),
                "Food": (city_count * 3000, nation["food"]),
                "Uranium": (city_count * 40, nation["uranium"]),
                "Gasoline": (city_count * 750, nation["gasoline"]),
                "Munitions": (city_count * 750, nation["munitions"]),
                "Steel": (city_count * 750, nation["steel"]),
                "Aluminum": (city_count * 750, nation["aluminum"]),
            }
    
            def get_completion_color(pct: float) -> str:
                if pct >= 76: return "🟢"
                if pct >= 51: return "🟡"
                if pct >= 26: return "🟠"
                if pct >= 10: return "🔴"
                return "⚫"
    
            def format_missing(name, missing, current):
                total = missing + current
                pct = (current / total) * 100 if total > 0 else 100
                return f"{round(missing):,} {name} missing {get_completion_color(pct)} ({pct:.0f}% complete)"
    
            missing_lines = [
                format_missing(name, max(0, need - have), have)
                for name, (need, have) in requirements.items()
            ]
    
            description = (
                "✅ **All materials present**"
                if all("🟢" in line for line in missing_lines)
                else "\n".join(missing_lines)
            )
    
            embed = discord.Embed(
                title="Warchest Audit",
                description=f"**Nation:** {nation['nation_name']} (`{nation_id}`)\n"
                            f"**Missing Materials:**\n{description}",
                color=discord.Color.gold()
            )
            embed.set_footer(
                text="Brought to you by Darkstar",
                icon_url="https://i.ibb.co/qJygzr7/Leonardo-Phoenix-A-dazzling-star-emits-white-to-bluish-light-s-2.jpg"
            )
    
            self.clear_items()
            self.add_item(BackButton(self.original_embed, self))  # ← ensures back returns to original view
            self.add_item(CloseButton())
    
            await interaction.message.edit(embed=embed, view=self)
    
        except Exception as e:
            await interaction.followup.send(f"❌ Error while running audit: {e}", ephemeral=True)
            
    @discord.ui.button(label="MMR", style=discord.ButtonStyle.primary)
    async def mmr_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        nation_id = self.nation_id
    
        try:
            GRAPHQL_URL = f"https://api.politicsandwar.com/graphql?api_key={API_KEY}"
    
            query = """
            query GetNationData($id: [Int]) {
                nations(id: $id) {
                    data {
                        nation_name
                        num_cities
                        cities {
                            name
                            barracks
                            factory
                            hangar
                            drydock
                        }
                    }
                }
            }
            """
            variables = {"id": [int(nation_id)]}
            response = requests.post(
                GRAPHQL_URL,
                json={"query": query, "variables": variables},
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            data = response.json()
            print("GraphQL Raw Response:", data)
    
            nation_list = data.get("data", {}).get("nations", {}).get("data", [])
            if not nation_list:
                await interaction.followup.send("❌ No nation data found.", ephemeral=True)
                return
    
            nation_data = nation_list[0]
            nation_name = nation_data.get("nation_name", "Unknown Nation")
            num_cities = nation_data.get("num_cities", 0)
            cities = nation_data.get("cities", [])
    
            barracks = sum(city.get("barracks", 0) for city in cities)
            factory = sum(city.get("factory", 0) for city in cities)
            hangar = sum(city.get("hangar", 0) for city in cities)
            drydocks = sum(city.get("drydock", 0) for city in cities)
    
            military_data = get_military(nation_id)
            if military_data is None:
                await interaction.followup.send("❌ Could not retrieve military data for this nation.", ephemeral=True)
                return
    
            (
                nation_name,
                leader_name,
                score,
                warpolicy,
                soldiers,
                tanks,
                aircraft,
                ships,
                spies,
                missiles,
                nukes,
            ) = military_data
    
            valid_mmrs = (
                [[0, 5, 5, 1], [5, 5, 5, 3]] if num_cities < 16 else [[0, 3, 5, 1], [5, 5, 5, 3]]
            )
    
            from collections import Counter
    
            def distribute_structures(total, parts):
                if parts == 0:
                    return []
                base = total // parts
                extras = total % parts
                return [base + (1 if i < extras else 0) for i in range(parts)]
    
            b_list = distribute_structures(barracks, num_cities)
            f_list = distribute_structures(factory, num_cities)
            h_list = distribute_structures(hangar, num_cities)
            d_list = distribute_structures(drydocks, num_cities)
    
            city_mmrs = list(zip(b_list, f_list, h_list, d_list))
            mmr_counts = Counter(city_mmrs)
    
            is_valid = all([b, f, h, d] in valid_mmrs for (b, f, h, d) in city_mmrs)
    
            grouped_mmr_string = "\n".join(
                f"{count} Cities: {b}/{f}/{h}/{d}" for (b, f, h, d), count in sorted(mmr_counts.items(), reverse=True)
            ) or "No cities"
    
            valid_options = "\n".join(f"{m[0]}/{m[1]}/{m[2]}/{m[3]}" for m in valid_mmrs)
    
            embed = discord.Embed(
                title=f"MMR Audit for {nation_name}",
                color=discord.Color.green() if is_valid else discord.Color.red(),
            )
            embed.add_field(name="Cities", value=str(num_cities), inline=False)
            embed.add_field(name="Grouped City MMRs", value=grouped_mmr_string, inline=False)
            embed.add_field(name="Soldiers", value=f"{soldiers}/{barracks*3000} (Missing {barracks*3000 - soldiers})", inline=False)
            embed.add_field(name="Tanks", value=f"{tanks}/{factory*250} (Missing {factory*250 - tanks})", inline=False)
            embed.add_field(name="Aircrafts", value=f"{aircraft}/{hangar*15} (Missing {hangar*15 - aircraft})", inline=False)
            embed.add_field(name="Ships", value=f"{ships}/{drydocks*5} (Missing {drydocks*5 - ships})", inline=False)
            embed.add_field(name="Status", value="✅ Valid MMR" if is_valid else "❌ Invalid MMR", inline=False)
            if not is_valid:
                embed.add_field(name="Valid Options", value=valid_options, inline=False)
    
            embed.set_footer(
                text="Brought to you by Darkstar",
                icon_url="https://i.ibb.co/qJygzr7/Leonardo-Phoenix-A-dazzling-star-emits-white-to-bluish-light-s-2.jpg"
            )
    
            # Add Back and Close buttons same as your Warchest button does:
            self.clear_items()
            self.add_item(BackButton(self.original_embed, self))  # assumes you have these button classes
            self.add_item(CloseButton())
    
            await interaction.message.edit(embed=embed, view=self)
    
        except Exception as e:
            await interaction.followup.send(f"❌ An error occurred during MMR audit: {e}", ephemeral=True)

class BackButton(discord.ui.Button):
    def __init__(self, original_embed, parent_view):
        super().__init__(label="Back", style=discord.ButtonStyle.success)
        self.original_embed = original_embed
        self.parent_view = parent_view

    async def callback(self, interaction: discord.Interaction):
        self.parent_view.clear_items()
        self.parent_view.add_item(self.parent_view.builds_button)
        self.parent_view.add_item(self.parent_view.projects_button)
        self.parent_view.add_item(self.parent_view.audit_button)
        self.parent_view.add_item(CloseButton())

        await interaction.response.edit_message(embed=self.original_embed, view=self.parent_view)

class CloseButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Close", style=discord.ButtonStyle.danger)

    async def callback(self, interaction: discord.Interaction):
        await interaction.message.delete()
        self.view.stop()

BANK_PERMISSION_TYPE = "Nation Deposit to Bank"

class AmountModal(discord.ui.Modal, title="Enter Amount"):
    amount = discord.ui.TextInput(label="How much?", placeholder="e.g., 50", required=True)

    def __init__(self, on_submit):
        super().__init__()
        self.on_submit_callback = on_submit

    async def on_submit(self, interaction: discord.Interaction):
        await self.on_submit_callback(interaction, self.amount.value)

class MessageView(View):
    def __init__(self, description_text):
        super().__init__()
        self.description_text = description_text

    @discord.ui.button(label="Generate Message", style=discord.ButtonStyle.green, custom_id="gm_message_button")
    async def copy_message_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Define the modal
        class AmountModal(discord.ui.Modal, title="Select Warchest Percentage"):
            amount = discord.ui.TextInput(
                label="Warchest Percentage",
                placeholder="50% or 100%",
                required=True,
                max_length=4
            )

            def __init__(self, on_submit):
                super().__init__()
                self.on_submit_callback = on_submit

            async def on_submit(self, interaction: discord.Interaction):
                await self.on_submit_callback(interaction, self.amount.value)

        # Define what to do with the result
        async def handle_submit(interaction: discord.Interaction, how_much: str):
            await interaction.response.defer()
            if how_much == "100%":
                what = f"Use the `/request_warchest` command in <#1338510585595428895> and request a `100% warchest`."
            elif how_much == "50%":
                what = f"Use the `/request_warchest` command in <#1338510585595428895> and request a `50% warchest`. You don't really need a 100% warchest atm"
            else:
                what = f"Invalid percentage provided: `{how_much}`"

            await interaction.followup.send(
                f"You are missing the following:\n"
                f"{self.description_text}\n\n"
                f"{what}"
            )

        # Show modal
        await interaction.response.send_modal(AmountModal(on_submit=handle_submit))

from discord.ui import View, button
from discord import ButtonStyle

class MMRView(View):
    def __init__(self, is_valid, soldiers, barracks, factory, tanks, aircraft, ships, drydocks, hangars, num_cities):
        super().__init__(timeout=None)
        self.is_valid = is_valid
        self.soldiers = soldiers
        self.barracks = barracks
        self.factory = factory
        self.tanks = tanks
        self.aircraft = aircraft
        self.ships = ships
        self.drydocks = drydocks
        self.hangars = hangars
        self.num_cities = num_cities

    @button(label="Fix MMR", style=ButtonStyle.red)
    async def fix_mmr(self, interaction, button):
        if self.is_valid:
            await interaction.response.send_message(
                "Your MMR is already valid! No need to fix it."
            )
        else:
            # Peace MMR depends on city count
            peace_mmr = "0/5/5/1" if self.num_cities <= 15 else "0/3/5/1"
            war_mmr = "5/5/5/3"
            await interaction.response.send_message(
                f"Please, get that MMR to either war MMR (option={war_mmr}) or peacetime MMR (option={peace_mmr})."
            )
        await interaction.message.edit(view=None)

    @button(label="Buy Troops", style=ButtonStyle.blurple)
    async def buy_troops(self, interaction, button):
        if not self.is_valid:
            await interaction.response.send_message(
                "MMR is invalid. Please fix your MMR first."
            )
            return

        missing = []
        max_soldiers = self.barracks * 3000
        max_tanks = self.factory * 250
        max_aircraft = self.hangars * 15
        max_ships = self.drydocks * 5

        if self.soldiers < max_soldiers:
            missing.append(f"{max_soldiers - self.soldiers} soldiers")
        if self.tanks < max_tanks:
            missing.append(f"{max_tanks - self.tanks} tanks")
        if self.aircraft < max_aircraft:
            missing.append(f"{max_aircraft - self.aircraft} aircraft")
        if self.ships < max_ships:
            missing.append(f"{max_ships - self.ships} ships")

        if not missing:
            await interaction.response.send_message(
                "Your troops are all stocked up. No need to buy more."
            )
            await interaction.message.edit(view=None)
            return

        if len(missing) == 1:
            msg = missing[0]
        else:
            msg = ", ".join(missing[:-1]) + " and " + missing[-1]

        await interaction.response.send_message(
            f"The MMR is looking good, but please buy your troops: {msg}."
        )
        await interaction.message.edit(view=None)

    @button(label="Close", style=ButtonStyle.gray)
    async def close(self, interaction, button):
        await interaction.response.send_message(
            "Looking good. Nothing to complain about."
        )
        await interaction.message.edit(view=None)
        self.stop()



class BlueGuy(discord.ui.View):
    def __init__(self, category=None, data=None):
        super().__init__(timeout=None)
        self.category = category
        self.data = data or {}

    @discord.ui.button(label="Request Grant", style=discord.ButtonStyle.green, custom_id="req_money_needed")
    async def send_request(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        person = str(self.data.get("person", None))
        print(person)
        presser = str(interaction.user.id)
        print(presser)
        if presser != person:
            if presser not in ["1378012299507269692", "1148678095176474678"]:
                await interaction.followup.send("No :wilted_rose:", ephemeral=True)
                return

        embed = discord.Embed(title="Request Grant", color=discord.Color.green())

        reason = "Unknown Request"
        materials = {}
        nation_name = self.data.get("nation_name", "?")
        nation_id = self.data.get("nation_id", "unknown")

        # Set up Reason and Materials
        if self.category == "infra":
            from_level = self.data.get("from", "?")
            to_level = self.data.get("infra", "?")
            cities = self.data.get("ct_count", "?")
            reason = f"Upgrade infrastructure from {from_level} to {to_level} in {cities} cities"
            materials = {"Money": self.data.get("total_cost", 0)}

        elif self.category == "city":
            from_cities = self.data.get("from", "?")
            to_cities = self.data.get("city_num", "?")
            ct_num = to_cities - from_cities
            reason = f"City {from_cities} - {to_cities}"
            materials = {"Money": self.data.get("total_cost", 0)}

        elif self.category == "project":
            project_name = self.data.get("project_name", "?")
            reason = f"Build project: {project_name}"
            materials = self.data.get("materials", {})

        # Start embed description
        description_lines = [f"**Nation:** {nation_name} (`{nation_id}`)", "**Request:**"]
        if materials:
            for name, amount in materials.items():
                description_lines.append(f"{name}: {amount:,.0f}")
        else:
            description_lines.append("None")

        description_lines.append(f"\n**Requested by:** <@{presser}>")
        embed.description = "\n".join(description_lines)

        # Reason field
        embed.add_field(name="Reason", value=reason, inline=False)

        # Footer
        image_url = "https://i.ibb.co/qJygzr7/Leonardo-Phoenix-A-dazzling-star-emits-white-to-bluish-light-s-2.jpg"
        embed.set_footer(text="Brought to you by Darkstar", icon_url=image_url)

        await interaction.message.edit(embed=embed, view=GrantView())

class GrantView(View):
    def __init__(self):
        super().__init__(timeout=None)

    async def is_government_member(self, interaction):
        return (
            any(role.name == "Banker" for role in interaction.user.roles)
            or str(interaction.user.id) == "1148678095176474678"
        )

    @button(label="✅ Sent", style=discord.ButtonStyle.green, custom_id="grant_approve")
    async def approve_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self.is_government_member(interaction):
            try:
                await interaction.response.send_message("❌ You need the 'Banker' role to approve grant requests.", ephemeral=True)
            except discord.NotFound:
                pass  # interaction might have expired
            return

        try:
            embed = interaction.message.embeds[0]
            embed.color = discord.Color.green()
            embed.description += f"\n**Status:** ✅ **GRANT SENT**"

            image_url = "https://i.ibb.co/qJygzr7/Leonardo-Phoenix-A-dazzling-star-emits-white-to-bluish-light-s-2.jpg"
            embed.set_footer(text="Brought to you by Darkstar", icon_url=image_url)

            await interaction.message.edit(embed=embed, view=None)

            lines = embed.description.splitlines()
            user_mention = "@someone"
            for line in lines:
                if line.startswith("**Requested by:**"):
                    user_mention = line.split("**Requested by:**")[1].strip()
                    break

            try:
                await interaction.followup.send(f"✅ Grant request has been approved and sent! {user_mention}", ephemeral=False)
            except discord.NotFound:
                # Fallback if followup webhook is expired
                await interaction.channel.send(f"✅ Grant request has been approved and sent! {user_mention}")

        except Exception as e:
            try:
                await interaction.followup.send(f"❌ Error: `{e}`", ephemeral=True)
            except discord.NotFound:
                await interaction.channel.send(f"❌ Error (no followup): `{e}`")


    @button(label="🕒 Delay", style=discord.ButtonStyle.primary, custom_id="grant_delay")
    async def delay_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self.is_government_member(interaction):
            await interaction.response.send_message("❌ You need the 'Banker' role to approve grant requests.", ephemeral=True)
            return

        try:
            embed = interaction.message.embeds[0]
            embed.color = discord.Color.orange()
            embed.description += f"\n**Status:** 🕒 **DELAYED**"
            image_url = "https://i.ibb.co/qJygzr7/Leonardo-Phoenix-A-dazzling-star-emits-white-to-bluish-light-s-2.jpg"
            embed.set_footer(text=f"Brought to you by Darkstar", icon_url=image_url)

            new_view = GrantView()
            new_view.remove_item(new_view.children[1]) 

            await interaction.message.edit(embed=embed, view=new_view)
            await interaction.message.pin()
            await interaction.response.send_message("✅ Grant delayed and message pinned.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error: `{e}`", ephemeral=True)

    @button(label="❌ Deny", style=discord.ButtonStyle.red, custom_id="grant_denied")
    async def deny_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self.is_government_member(interaction):
            await interaction.response.send_message("❌ You need the 'Banker' role to deny grant requests.", ephemeral=True)
            return
        try:
            embed = interaction.message.embeds[0]
            embed.color = discord.Color.red()
            embed.description += f"\n**Status:** ❌ **GRANT DENIED**"
            image_url = "https://i.ibb.co/qJygzr7/Leonardo-Phoenix-A-dazzling-star-emits-white-to-bluish-light-s-2.jpg"
            embed.set_footer(text=f"Brought to you by Darkstar", icon_url=image_url)
            await interaction.message.edit(embed=embed, view=None)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error: `{e}`", ephemeral=True)

    @button(label="Copy Command", style=discord.ButtonStyle.blurple, custom_id="copied")
    async def copy_command(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self.is_government_member(interaction):
            await interaction.response.send_message("❌ You need the 'Banker' role to approve grant requests.", ephemeral=True)
            return

        try:
            embed = interaction.message.embeds[0]
            lines = embed.description.splitlines()

            nation_line = next((line for line in lines if line.startswith("**Nation:**")), None)
            nation_id = nation_line.split("(`")[1].strip("`)") if nation_line else "unknown"

            try:
                request_start = lines.index("**Request:**") + 1
            except ValueError:
                await interaction.response.send_message("❌ Could not find '**Request:**' in embed.", ephemeral=True)
                return

            try:
                reason_index = next(i for i, line in enumerate(lines) if line.startswith("**Reason:**"))
            except StopIteration:
                reason_index = len(lines)

            request_lines = lines[request_start:reason_index]

            abbr_map = {
                "Money": "-$",
                "Gasoline": "-g",
                "Munitions": "-m",
                "Steel": "-s",
                "Aluminum": "-a",
                "Food": "-f",
                "Oil": "-o",
                "Uranium": "-u",
                "Lead": "-l",
                "Iron": "-i",
                "Bauxite": "-b",
                "Coal": "-c",
            }

            command_parts = [f"$tfo -t https://politicsandwar.com/nation/id={nation_id}"]
            for line in request_lines:
                if ":" not in line:
                    continue
                key, val = [x.strip() for x in line.split(":", 1)]
                if key not in abbr_map:
                    continue
                val = val.replace(".", "").replace(",", "").strip()
                try:
                    num = int(val)
                    command_parts.append(f"{abbr_map[key]} {num}")
                except ValueError:
                    continue

            await interaction.response.send_message(f"***TARS COMMAND: {' '.join(command_parts)}***", ephemeral=True)

        except Exception as e:
            await interaction.response.send_message(f"❌ Error parsing embed: `{e}`", ephemeral=True)

class RawsAuditView(discord.ui.View):
    def __init__(self, output, audits):
        super().__init__(timeout=None)
        self.output = output
        self.audits = audits  # Expects each entry to include a "color" key

    @discord.ui.button(label="Request Yellow", style=discord.ButtonStyle.primary, custom_id="request_yellow")
    async def request_yellow(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_request(interaction, "🟡", discord.Color.yellow())

    @discord.ui.button(label="Request Orange", style=discord.ButtonStyle.primary, custom_id="request_orange")
    async def request_orange(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_request(interaction, "🟠", discord.Color.orange())

    @discord.ui.button(label="Request Red", style=discord.ButtonStyle.danger, custom_id="request_red")
    async def request_red(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_request(interaction, "🔴", discord.Color.red())

    async def handle_request(self, interaction: discord.Interaction, color_emoji: str, embed_color: discord.Color):
        await interaction.response.defer(ephemeral=True)

        user_id = interaction.user.id
        bot = interaction.client

        guild = bot.get_guild(1186655069530243183)
        if not guild:
            await interaction.followup.send("❌ Target guild not found.")
            return

        channel = guild.get_channel(1338510585595428895)
        if not channel:
            await interaction.followup.send("❌ Target channel not found.")
            return

        sheet = get_registration_sheet()
        rows = sheet.get_all_records()

        for nation_id, entry in self.audits.items():
            nation_name = entry["nation_name"]
            missing_resources = entry.get("missing", [])
        
            relevant_lines = [
                f"{res_name}: {float(amount):.2f}"
                for res_name, amount, res_color in missing_resources
                if res_color == color_emoji
            ]
        
            if not relevant_lines:
                continue  # No missing resources of the requested color in this nation, skip

            row = next((r for r in rows if str(r.get("NationID", "")).strip() == str(nation_id)), None)
            if not row:
                continue

            discord_id = row.get("DiscordID", None)
            if not discord_id:
                continue

            embed = discord.Embed(
                title="Resource Request",
                description=(
                    f"**Nation:** {nation_name} (`{nation_id}`)\n"
                    f"**Request:**\n" + "\n".join(relevant_lines) + "\n"
                    f"**Reason:** Resources for Production\n"
                    f"**Requested by:** <@{discord_id}>"
                ),
                color=embed_color
            )
            image_url = "https://i.ibb.co/qJygzr7/Leonardo-Phoenix-A-dazzling-star-emits-white-to-bluish-light-s-2.jpg"
            embed.set_footer(text="Brought to you by Darkstar", icon_url=image_url)

            await channel.send(embed=embed, view=GrantView())

        await interaction.followup.send(f"✅ Processed {color_emoji} requests.")

class AccountApprovalView(discord.ui.View):
    def __init__(self, user_id, aa_name=None, nation_id=None):
        super().__init__()
        self.user_id = user_id
        self.aa_name = aa_name
        self.nation_id = nation_id

    @discord.ui.button(label="Approve", style=discord.ButtonStyle.green)
    async def approve(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            if self.aa_name:
                create_aa_account(self.user_id, self.aa_name, self.nation_id)
                await interaction.response.send_message(
                    f"✅ Created AA account `{self.aa_name}` for <@{self.user_id}>.", ephemeral=True
                )
            else:
                create_account(self.user_id, self.nation_id)
                await interaction.response.send_message(
                    f"✅ Created personal account for <@{self.user_id}>.", ephemeral=True
                )
        except Exception as e:
            await interaction.response.send_message(f"❌ Error creating account: {e}", ephemeral=True)
        self.stop()


class TradeButton(discord.ui.View):
    def __init__(self, author: discord.User, request_data: dict, message: discord.Message):
        super().__init__(timeout=None)
        self.author = author
        self.message = message
        self.request_data = request_data

    @discord.ui.select(
        placeholder="Choose what you're doing...",
        options=[
            discord.SelectOption(label="I want to offer this", value="offer"),
            discord.SelectOption(label="I also want to receive this", value="receive"),
        ]
    )
    async def select_callback(self, interaction: discord.Interaction, select: discord.ui.Select):
        # Add original message ID to thread name so we can track it later
        thread = await interaction.channel.create_thread(
            name=f"Trade-{self.message.id}-{interaction.user.display_name}",
            type=discord.ChannelType.public_thread,
            auto_archive_duration=60
        )

        requester_embed = discord.Embed(
            title="📦 Trade Request Summary",
            description=(
                f"**{self.author.mention} requested:**\n"
                + "\n".join(f"{k}: {v:,}".replace(",", ".") for k, v in self.request_data.items())
                + f"\n\n➡️ **{interaction.user.mention} responded:** `{select.values[0]}`\n"
            ),
            color=discord.Color.green()
        )

        await thread.send(
            content=f"{self.author.mention} {interaction.user.mention}",
            embed=requester_embed,
            view=EndTradeView(original_message=self.message, author_id=self.author.id)
        )

        await interaction.response.send_message(f"✅ Trade thread created: {thread.mention}", ephemeral=True)


class EndTradeView(discord.ui.View):
    def __init__(self, original_message: discord.Message, author_id: int):
        super().__init__(timeout=None)
        self.original_message = original_message
        self.author_id = author_id

    @discord.ui.button(label="✅ End Trade", style=discord.ButtonStyle.danger)
    async def end_trade_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("Only the trade creator can end the trade.", ephemeral=True)
            return

        deleted = 0
        for thread in interaction.guild.threads:
            # Now this will find threads with the original message ID in their name
            if str(self.original_message.id) in thread.name:
                try:
                    await thread.delete()
                    deleted += 1
                except Exception:
                    pass

        embed = self.original_message.embeds[0]
        embed.title = "✅ Trade Ended"
        embed.description += f"\n\nTrade closed by {interaction.user.mention}."
        embed.color = discord.Color.dark_gray()

        try:
            await self.original_message.edit(embed=embed, view=None)
        except Exception:
            pass

        await interaction.response.send_message(f"✅ Trade ended. {deleted} thread(s) deleted.", ephemeral=True)



def get_military_o(nation_id):
    session = requests.Session()
    url = f"https://politicsandwar.com/nation/id={nation_id}"
    response = session.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')

    def extract_stat(label_text):
        label = soup.find(string=lambda s: s and label_text in s)
        if not label or not label.parent:
            return "❌ Not Found"
        td = label.parent.find_next_sibling("td")
        if not td:
            return "❌ Missing Data"
        return "".join(t for t in td.find_all(string=True, recursive=False)).strip()

    def get_first_value(value):
        return value.split()[0]

    nation_name = extract_stat("Nation Name:")
    nation_leader = extract_stat("Leader Name:")
    nation_rank = extract_stat("Nation Rank:")
    nation_score = extract_stat("Nation Score:")
    war_policy = extract_stat("War Policy:")
    soldiers = get_first_value(extract_stat("Soldiers:"))
    tanks = get_first_value(extract_stat("Tanks:"))
    aircraft = get_first_value(extract_stat("Aircraft:"))
    ships = get_first_value(extract_stat("Ships:"))
    spies = get_first_value(extract_stat("Spies:"))
    missiles = get_first_value(extract_stat("Missiles:"))
    nuclear = get_first_value(extract_stat("Nuclear Weapons:"))

    return nation_name, nation_leader, nation_rank, nation_score, war_policy, soldiers, tanks, aircraft, ships, spies, missiles, nuclear
    
def graphql_cities(nation_id):
    GRAPHQL_URL = f"https://api.politicsandwar.com/graphql?api_key={API_KEY}"

    # Add project fields separately from cities
    project_fields = "\n".join(PROJECT_KEYS)

    query = f"""
    {{
      nations(id: [{nation_id}]) {{
        data {{
          num_cities
          {project_fields}
          cities {{
            name
            id
            infrastructure
            land
            powered
            oil_power
            wind_power
            coal_power
            nuclear_power
            coal_mine
            oil_well
            uranium_mine
            barracks
            farm
            police_station
            hospital
            recycling_center
            subway
            supermarket
            bank
            shopping_mall
            stadium
            lead_mine
            iron_mine
            bauxite_mine
            oil_refinery
            aluminum_refinery
            steel_mill
            munitions_factory
            factory
            hangar
            drydock
          }}
        }}
      }}
    }}
    """

    try:
        response = requests.post(
            GRAPHQL_URL,
            json={"query": query},
            headers={"Content-Type": "application/json"}
        )
        response.raise_for_status()
        json_data = response.json()

        if "errors" in json_data:
            print("GraphQL Errors:", json_data["errors"])
            return None

        nations_data = json_data.get("data", {}).get("nations", {}).get("data", [])
        if not nations_data:
            print("No nation data found.")
            return None

        df = pd.json_normalize(nations_data)
        return df

    except requests.RequestException as e:
        print(f"HTTP Error during GraphQL request: {e}")
        return None
    except (KeyError, TypeError, json.JSONDecodeError) as e:
        print(f"Parsing Error: {e}")
        return None

def graphql_request(nation_id):
    GRAPHQL_URL = f"https://api.politicsandwar.com/graphql?api_key={API_KEY}"

    query = f"""
    {{
      nations(id: [{nation_id}]) {{
        data {{
          id
          nation_name
          leader_name
          last_active
          alliance_id
          alliance_position
          alliance {{ name }}
          color
          war_policy
          domestic_policy
          projects
          turns_since_last_project
          continent
          num_cities
          score
          population
          vmode
          beigeturns
          soldiers
          tanks
          aircraft
          ships
          missiles
          nukes
          espionage_available
          spies
          money
          coal
          oil
          uranium
          iron
          bauxite
          lead
          gasoline
          munitions
          steel
          aluminum
          food
        }}
      }}
    }}
    """

    try:
        response = requests.post(
            GRAPHQL_URL,
            json={"query": query},
            headers={"Content-Type": "application/json"}
        )
        response.raise_for_status()
        json_data = response.json()

        if "errors" in json_data:
            print("GraphQL Errors:", json_data["errors"])
            return None

        nations_data = json_data.get("data", {}).get("nations", {}).get("data", [])
        if not nations_data:
            print("No nation data found.")
            return None

        df = pd.json_normalize(nations_data)
        return df

    except requests.RequestException as e:
        print(f"HTTP Error during GraphQL request: {e}")
        return None
    except (KeyError, TypeError, json.JSONDecodeError) as e:
        print(f"Parsing Error: {e}")
        return None

def extract_cities_from_df(df):
    if df is None or df.empty:
        return None
    try:
        cities = df.at[0, "cities"]
        return cities
    except Exception as e:
        print(f"Error extracting cities from df: {e}")
        return None

def get_resources(nation_id):
    df = graphql_request(nation_id)
    if df is not None:
        try:
            row = df[df["id"].astype(str) == str(nation_id)].iloc[0]

            return (
                row.get("nation_name", ""),
                row.get("num_cities", 0),
                row.get("food", 0),
                row.get("money", 0),
                row.get("gasoline", 0),
                row.get("munitions", 0),
                row.get("steel", 0),
                row.get("aluminum", 0),
                row.get("bauxite", 0),
                row.get("lead", 0),
                row.get("iron", 0),
                row.get("oil", 0),
                row.get("coal", 0),
                row.get("uranium", 0),
            )
        except IndexError:
            return None

def get_general_data(nation_id):
    df = graphql_request(nation_id)
    if df is not None:
        try:
            row = df[df["id"].astype(str) == str(nation_id)].iloc[0]
            return (
                row.get("alliance_id", "Unknown"),
                row.get("alliance_position", "Unknown"),
                row.get("alliance.name", "None/Unaffiliated"),
                row.get("domestic_policy", "Unknown"),
                row.get("num_cities", "/"),
                row.get("color", "Unknown"),
                row.get("last_active", "/"),
                row.get("projects", "Unknown"),
                row.get("turns_since_last_project", "/"),
            )
        except IndexError:
            return None

def get_military(nation_id):
    df = graphql_request(nation_id)
    if df is not None:
        try:
            row = df[df["id"].astype(str) == str(nation_id)].iloc[0]
            return (
                row.get("nation_name", ""),
                row.get("leader_name", ""),
                row.get("score", 0),
                row.get("war_policy", ""),
                row.get("soldiers", 0),
                row.get("tanks", 0),
                row.get("aircraft", 0),
                row.get("ships", 0),
                row.get("spies", 0),
                row.get("missiles", 0),
                row.get("nukes", 0)
            )
        except IndexError:
            return None



def calculation(name, a, b, policy, war_type):
    unit_price = UNIT_PRICES.get(name, 0)
    c = a - b

    if b == 0:
        res = 100 if a > 0 else 50
    elif a == 0:
        res = 0
    elif c == 0:
        res = 100
    elif a > b:
        res = min(100, (c / b) * 100)
    else:
        res = 0

    if war_type == "Raid":
        res *= 1.25
    elif war_type == "Attrition":
        res *= 1.0

    if policy == "Pirate":
        res *= 1.4
    elif policy == "Attrition":
        res *= 1.1

    res = min(res, 100)

    opponent_value = b * unit_price
    win_value = (res / 100) * opponent_value
    fail_percent = 100 - res
    loss_value = (fail_percent / 100) * (a * unit_price)

    return {
        "success_chance": round(res, 2),
        "win_value": round(win_value, 2),
        "loss_value": round(loss_value, 2)
    }


# Load environment variables earl

import os
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import datetime
import asyncio
import traceback

# --- Google Sheets Credentials and Client Setup ---

def get_credentials():
    creds_str = os.environ.get("GOOGLE_CREDENTIALS")
    if not creds_str:
        raise RuntimeError("GOOGLE_CREDENTIALS not found in environment.")
    try:
        creds_json = json.loads(creds_str)
        return creds_json
    except Exception as e:
        raise RuntimeError(f"Failed to load GOOGLE_CREDENTIALS: {e}")

def get_client():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(get_credentials(), scope)
    client = gspread.authorize(creds)
    return client

# --- Sheet Access Functions ---

def get_registration_sheet():
    client = get_client()
    return client.open("Registrations").sheet1

def get_dm_sheet():
    client = get_client()
    return client.open("DmsSentByGov").sheet1

def get_alliance_sheet():
    client = get_client()
    return client.open("AllianceNet").sheet1

def get_conflict_sheet():
    client = get_client()
    return client.open("AllianceConflict").sheet1  # was incorrectly "Alliance Conflicts"

def get_conflict_data_sheet():
    client = get_client()
    return client.open("ConflictData").sheet1

def get_auto_requests_sheet():
    client = get_client()
    return client.open("AutoRequests").sheet1  # or .worksheet("SheetName") if needed
# --- Data Saving Functions ---

from datetime import datetime

import json
from datetime import datetime

import json
from datetime import datetime, timedelta

def get_bank_sheet():
    sheet = get_client().open("BankAccounts").sheet1
    headers = sheet.row_values(1)

    # Add missing columns without clearing existing data
    expected = [
    "owner", "aa_name", "money", "loans", "trading", "trust",
    "loan_history", "deposit_history", "loan_weekly", "loan_weeks_since",
    "members", "nation_id"
]

    if headers != expected:
        combined = list(headers)
        for h in expected:
            if h not in combined:
                combined.append(h)
        sheet.delete_row(1)
        sheet.insert_row(combined, index=1)

    return sheet


def get_account_row(user_id: str, aa_name: str):
    sheet = get_bank_sheet()
    records = sheet.get_all_records()
    for idx, row in enumerate(records, start=2):
        members = []
        try:
            members = json.loads(row.get("members", "[]"))
        except:
            pass
        if str(row["owner"]) == user_id or str(user_id) in members:
            if str(row["aa_name"]).lower() == aa_name.lower():
                return sheet, idx, row
    return sheet, None, None

def get_user_row(user_id):
    sheet = get_bank_sheet()
    records = sheet.get_all_records()
    for i, row in enumerate(records, start=2):
        if str(row["owner"]) == str(user_id) and not row["aa_name"].strip():
            return sheet, i, row
    return sheet, None, None

def append_history(sheet, idx, col_idx, entry):
    hist = json.loads(sheet.cell(idx, col_idx).value or "[]")
    hist.append(entry)
    sheet.update_cell(idx, col_idx, json.dumps(hist))

def update_weekly_payback(sheet, idx, loans, trust):
    weekly = (loans * (1 + trust * 12)) / 12
    sheet.update_cell(idx, 9, weekly)  # loan_weekly

def update_weeks_since(sheet, idx, history):
    if not history:
        weeks = 0
    else:
        last = datetime.fromisoformat(history[-1]["date"])
        weeks = (datetime.utcnow() - last).days // 7
    sheet.update_cell(idx, 10, weeks)


def create_account(user_id: str, nation_id: str):
    sheet = get_bank_sheet()
    sheet.append_row([
        user_id,
        "",         # aa_name
        0,          # money
        0,          # loans
        0,          # trading
        20000000,   # trust - will stay numeric with RAW
        json.dumps([]),
        json.dumps([]),
        0,
        0,
        json.dumps([user_id]),
        nation_id
    ], value_input_option="RAW")

def create_aa_account(user_id: str, aa_name: str, nation_id: str):
    sheet = get_bank_sheet()
    sheet.append_row([
        user_id,
        aa_name,
        0,
        0,
        0,
        20000000,
        json.dumps([]),
        json.dumps([]),
        0,
        0,
        json.dumps([user_id]),
        nation_id
    ], value_input_option="RAW")






def save_to_alliance_net(data_row):
    try:
        sheet = get_alliance_sheet()
        sheet.append_row(data_row)
        print("✅ Data saved to Alliance Net")
    except Exception as e:
        print(f"❌ Failed to save to Alliance Net: {e}")

def save_auto_request(user_id, nation_id, nation_name, resources, time_period):
    sheet = get_auto_requests_sheet()
    values = [
        user_id,
        nation_id,
        nation_name,
        str(resources.get("Uranium", 0)),
        str(resources.get("Coal", 0)),
        str(resources.get("Oil", 0)),
        str(resources.get("Bauxite", 0)),
        str(resources.get("Lead", 0)),
        str(resources.get("Iron", 0)),
        str(resources.get("Steel", 0)),
        str(resources.get("Aluminum", 0)),
        str(resources.get("Gasoline", 0)),
        str(resources.get("Money", 0)),
        str(resources.get("Food", 0)),
        str(resources.get("Munitions", 0)),
        str(time_period),
        "",  # LastRequested
    ]
    sheet.append_row(values)

def save_dm_to_sheet(sender_name, recipient_name, message):
    sheet = get_dm_sheet()
    headers = sheet.row_values(1)  # Assumes headers are in the first row
    data = {
        "Timestamp": datetime.now(timezone.utc).isoformat(),
        "Sender": sender_name,
        "Recipient": recipient_name,
        "Message": message
    }

    # Create the row in the correct order according to headers
    row = [data.get(header, "") for header in headers]
    sheet.append_row(row)

def save_conflict_row(data_row):
    try:
        sheet = get_conflict_data_sheet()
        sheet.append_row(data_row)
        print("✅ Conflict data saved")
    except Exception as e:
        print(f"❌ Failed to save conflict data: {e}")

def update_conflict_row(row_number, col_number, value):
    try:
        sheet = get_conflict_sheet()
        sheet.update_cell(row_number, col_number, value)
        print(f"✅ Conflict row {row_number} updated at column {col_number} with value: {value}")
    except Exception as e:
        print(f"❌ Failed to update conflict data: {e}")
        raise

def log_to_alliance_conflict(name, start, end=None, closed="False", enemy_ids="", message=""):
    try:
        sheet = get_conflict_sheet()
        records = sheet.get_all_values()
        for i, row in enumerate(records[1:], start=2):  # Skip header
            if row[0].strip().lower() == name.lower():
                if end:
                    sheet.update_cell(i, 3, end)
                # Optionally update other columns if needed
                return
        sheet.append_row([name, start, end or "", closed, enemy_ids, message])
        print(f"✅ Logged new conflict '{name}' to Alliance Conflict")
    except Exception as e:
        print(f"❌ Failed to log to Alliance Conflict: {e}")
        print(traceback.format_exc())


# --- Caching and Loading Sheet Data ---

cached_users = {}
cached_registrations = []
cached_conflicts = []
cached_conflict_data = []

def load_registration_data():
    global cached_users, cached_registrations
    try:
        sheet = get_registration_sheet()
        print(f"Sheet object: {sheet}")
        print(f"Sheet title: {sheet.title}")
        records = sheet.get_all_records()
        print(f"Records fetched: {len(records)}")
        cached_registrations = records
        cached_users = {
            str(record['DiscordID']): {
                'DiscordUsername': str(record['DiscordUsername']).strip().lower(),
                'NationID': str(record['NationID']).strip()
            }
            for record in records
        }
        print(f"✅ Loaded {len(cached_users)} users from registration sheet.")
    except Exception as e:
        print(f"❌ Failed to load registration sheet data: {e}")
        print(traceback.format_exc())

def load_conflict_data():
    global cached_conflict_data
    try:
        sheet = get_conflict_data_sheet()
        rows = sheet.get_all_values()
        print(f"Raw header row: {rows[0]}")
        print(f"Number of rows: {len(rows)}")
        print(f"First 3 rows:\n{rows[:3]}")


        if not rows:
            print("❌ Sheet is empty.")
            return None

        expected_header = [
            "Conflict Name", "War Start Date", "War End Date", "War ID",
            "Attacker Nation Name", "Defender Nation Name", "Result",
            "Money Gained", "Money Lost"
        ]

        actual_header = rows[0][:len(expected_header)]

        # Check for empty or duplicate headers
        if "" in actual_header:
            print(f"❌ Empty column name(s) in header: {actual_header}")
            return None
        if len(set(actual_header)) != len(actual_header):
            print(f"❌ Duplicate column names in header: {actual_header}")
            return None

        if actual_header != expected_header:
            print(f"❌ Header mismatch.\nExpected: {expected_header}\nActual:   {actual_header}")
            return None

        valid_rows = []
        for i, row in enumerate(rows[1:], start=2):
            if len(row) < len(expected_header):
                print(f"⚠️ Skipping row {i}: too short ({len(row)} columns)")
                continue
            if not row[3].isdigit():
                print(f"⚠️ Skipping row {i}: war ID is not numeric ({row[3]})")
                continue
            valid_rows.append(dict(zip(expected_header, row[:len(expected_header)])))

        cached_conflict_data = valid_rows
        print(f"✅ Loaded {len(valid_rows)} valid conflict data records.")
        return sheet

    except Exception as e:
        print(f"❌ Exception while loading conflict data: {e}")
        print(traceback.format_exc())
        return None

def load_conflicts_data():
    global cached_conflicts
    try:
        sheet = get_conflict_sheet()
        raw_data = sheet.get_all_records()
        # Strip whitespace from keys
        cached_conflicts = [{k.strip(): v for k, v in row.items()} for row in raw_data]
        if cached_conflicts:
            print(f"Headers: {list(cached_conflicts[0].keys())}")
            print(f"Sample conflict row: {cached_conflicts[0]}")
        print(f"✅ Loaded {len(cached_conflicts)} conflicts from sheet.")
        return sheet
    except Exception as e:
        print(f"❌ Failed to load conflicts sheet data: {e}")
        print(traceback.format_exc())
        return None


# --- Daily Refresh Task ---
from datetime import datetime, timezone
async def daily_refresh_loop():
    while True:
        now = datetime.now(timezone.utc)
        next_midnight = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        wait_seconds = (next_midnight - now).total_seconds()
        await asyncio.sleep(wait_seconds)
        print("🔄 Refreshing all cached sheet data at UTC midnight...")
        load_registration_data()
        load_conflicts_data()
        load_conflict_data()

# === Helper to find latest open conflict ===
def get_latest_open_conflict():
    conflicts = load_conflicts_data()
    for i, conflict in enumerate(reversed(conflicts), 1):
        if not conflict.get("Closed", False):
            return conflict, len(conflicts) - i + 2
    return None, None

def get_sheet():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(get_credentials(), scope)
    client = gspread.authorize(creds)
    return client.open("Registrations").sheet1

def load_sheet_data():
    global cached_users, cached_sheet_data
    try:
        load_registration_data()
        load_conflicts_data()
        load_conflict_data()
        bot.loop.create_task(daily_refresh_loop())
        sheet = get_sheet()
        print(f"Sheet object: {sheet}")
        print(f"Sheet title: {sheet.title}")
        records = sheet.get_all_records()
        print(f"Records fetched: {len(records)}")
        cached_sheet_data = records
        cached_users = {
            str(record['DiscordID']): {
                'DiscordUsername': str(record['DiscordUsername']).strip().lower(),
                'NationID': str(record['NationID']).strip()
            }
            for record in records
        }
        print(f"✅ Loaded {len(cached_users)} users from sheet.")
    except Exception as e:
        print(f"❌ Failed to load sheet data: {e}")
        print(traceback.format_exc())

@tasks.loop(hours=1)
async def process_auto_requests():
    GRANT_REQUEST_CHANNEL_ID = "1338510585595428895"
    REASON_FOR_GRANT = "Resources for Production (Auto)"

    try:
        sheet = get_auto_requests_sheet()
        all_rows = await asyncio.to_thread(sheet.get_all_values)
        if not all_rows or len(all_rows) < 2:
            return

        # Filter out empty columns from header
        header = [h.strip() for h in all_rows[0] if h.strip()]
        if len(header) != len(set(header)):
            raise ValueError(f"The header row contains duplicates or blanks: {header}")

        col_index = {col: idx for idx, col in enumerate(all_rows[0])}
        rows = all_rows[1:]

        guild = bot.get_guild(1186655069530243183)
        channel = guild.get_channel(int(GRANT_REQUEST_CHANNEL_ID)) if guild else None
        if channel is None:
            print("Grant request channel not found!")
            return

        now = datetime.now(timezone.utc)

        for i, row in enumerate(rows, start=2):
            try:
                nation_id = row[col_index.get("NationID", -1)].strip() if col_index.get("NationID", -1) != -1 else ""
                if not nation_id:
                    print(f"Skipping row {i} due to empty NationID")
                    continue

                # Get nation name
                nation_info_df = graphql_request(nation_id)
                nation_name = nation_info_df.loc[0, "nation_name"] if nation_info_df is not None and not nation_info_df.empty else "Unknown"

                discord_id = row[col_index["DiscordID"]].strip()
                time_period_days = int(float(row[col_index["TimePeriod"]].strip() or "1"))

                last_requested_str = row[col_index["LastRequested"]].strip()
                last_requested = (
                    datetime.strptime(last_requested_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
                    if last_requested_str else datetime.min.replace(tzinfo=timezone.utc)
                )

                if now - last_requested < timedelta(days=time_period_days):
                    continue

                requested_resources = {}
                for res in ["Coal", "Oil", "Bauxite", "Lead", "Iron"]:
                    val_str = row[col_index[res]].strip()
                    amount = parse_amount(val_str)
                    if amount > 0:
                        requested_resources[res] = amount

                if not requested_resources:
                    continue

                description_text = "\n".join([f"{resource}: {amount:,}".replace(",", ".") for resource, amount in requested_resources.items()])

                embed = discord.Embed(
                    title="💰 Grant Request",
                    color=discord.Color.gold(),
                    description=(
                        f"**Nation:** {nation_name} (`{nation_id}`)\n"
                        f"**Requested by:** <@{discord_id}>\n"
                        f"**Request:**\n{description_text}\n"
                        f"**Reason:** {REASON_FOR_GRANT}\n"
                    )
                )
                image_url = "https://i.ibb.co/qJygzr7/Leonardo-Phoenix-A-dazzling-star-emits-white-to-bluish-light-s-2.jpg"
                embed.set_footer(text="Brought to you by Darkstar", icon_url=image_url)

                await channel.send(embed=embed, view=GrantView())

                # Update timestamp
                await asyncio.to_thread(sheet.update_cell, i, col_index["LastRequested"] + 1, now.strftime("%Y-%m-%d %H:%M:%S"))

            except Exception as inner_ex:
                print(f"Error processing row {i}: {inner_ex}")

    except Exception as ex:
        print(f"Error in process_auto_requests task: {ex}")

import asyncio

@tasks.loop(hours=1)
async def hourly_war_check():
    print(f"⏰ Running hourly war check at {datetime.utcnow().strftime('%H:%M:%S')} UTC...")
    await perform_war_check_logic()

@hourly_war_check.before_loop
async def before_hourly_check():
    now = datetime.utcnow()
    next_hour = (now + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)
    wait_seconds = (next_hour - now).total_seconds()
    print(f"⏳ Waiting {int(wait_seconds)}s until next full hour...")
    await asyncio.sleep(wait_seconds)

async def perform_war_check_logic():
    try:
        load_conflicts_data()
        active_conflicts = [
            c for c in cached_conflicts
            if str(c.get("Closed", "")).strip().lower() != "true"
            and c.get("Name")
            and c.get("EnemyIDs")
        ]

        if not active_conflicts:
            print("⏳ No active conflicts. Skipping check.")
            return

        conflict = active_conflicts[0]
        conflict_name = conflict.get("Name")
        conflict_start_date = conflict.get("Start") or conflict.get("StartDate")
        if not conflict_start_date:
            print(f"⚠️ Conflict '{conflict_name}' has no start date. Skipping.")
            return

        try:
            enemy_ids = [int(id.strip()) for id in str(conflict.get("EnemyIDs")).split(",") if id.strip().isdigit()]
        except Exception as e:
            print(f"❌ Failed to parse enemy IDs: {e}")
            return

        if not enemy_ids:
            print(f"⚠️ No valid enemy alliance IDs set for conflict '{conflict_name}'")
            return

        GRAPHQL_URL = f"https://api.politicsandwar.com/graphql?api_key={API_KEY}"
        headers = {"Content-Type": "application/json"}
        query = """
        query AllianceWars($id: [Int], $limit: Int) {
          alliances(id: $id) {
            data {
              id
              name
              wars(limit: $limit) {
                id
                date
                end_date
                winner_id
                attacker {
                  id
                  nation_name
                  alliance_id
                  wars {
                    id
                    attacks { money_stolen }
                  }
                }
                defender {
                  id
                  nation_name
                  alliance_id
                  wars {
                    id
                    attacks { money_stolen }
                  }
                }
              }
            }
          }
        }
        """
        variables = {"id": [10259], "limit": 500}
        try:
            response = requests.post(GRAPHQL_URL, json={"query": query, "variables": variables}, headers=headers)
            response.raise_for_status()
            result = response.json()
        except Exception as e:
            print(f"❌ API request failed: {e}")
            return

        alliances_data = result.get("data", {}).get("alliances", {}).get("data", [])
        if not alliances_data:
            print("❌ No data returned from API.")
            return

        sheet = get_conflict_data_sheet()
        existing_rows = sheet.get_all_values()
        existing_war_ids = set(str(row[3]) for row in existing_rows[1:] if len(row) > 3 and row[3])

        all_new_wars = []

        for alliance in alliances_data:
            for war in alliance.get("wars", []):
                war_id = str(war.get("id"))
                end_date = war.get("end_date")
                start_date = war.get("date", "")[:10]

                # Skip if active or already logged
                if not end_date or war_id in existing_war_ids:
                    continue

                if start_date != conflict_start_date:
                    continue

                war_end = end_date[:10]
                attacker_data = war.get("attacker", {})
                defender_data = war.get("defender", {})

                if not attacker_data or not defender_data:
                    continue

                attacker = attacker_data.get("nation_name")
                defender = defender_data.get("nation_name")
                if not attacker or not defender:
                    continue

                winner_id = war.get("winner_id")
                result_str = (
                    "Attacker" if winner_id == attacker_data.get("id") else
                    "Defender" if winner_id == defender_data.get("id") else
                    "Draw"
                )

                att_money = sum((a.get("money_stolen") or 0) for w in attacker_data.get("wars", []) for a in w.get("attacks", []))
                def_money = sum((a.get("money_stolen") or 0) for w in defender_data.get("wars", []) for a in w.get("attacks", []))

                money_gained = att_money if attacker_data.get("alliance_id") == 10259 else def_money
                money_lost = def_money if attacker_data.get("alliance_id") == 10259 else att_money

                row = [
                    conflict_name,
                    start_date,
                    war_end,
                    war_id,
                    attacker,
                    defender,
                    result_str,
                    f"{money_gained:.2f}",
                    f"{money_lost:.2f}"
                ]

                if len(row) == 9 and all(row):
                    all_new_wars.append(row)

        # Append in batches
        batch_size = 30
        total = len(all_new_wars)
        for i in range(0, total, batch_size):
            batch = all_new_wars[i:i+batch_size]
            try:
                sheet.append_rows(batch)
                print(f"📥 Logged {len(batch)} wars [{i + 1}-{i + len(batch)} of {total}] for conflict '{conflict_name}'.")
            except Exception as e:
                print(f"❌ Failed to append batch: {e}")
            if i + batch_size < total:
                print("⏳ Waiting 60 seconds before next batch...")
                await asyncio.sleep(70)

    except Exception as e:
        print(f"❌ Error in hourly war check: {e}")



@tasks.loop(hours=1)
async def hourly_snapshot():
    now = datetime.now(timezone.utc)
    current_hour = now.replace(minute=0, second=0, microsecond=0)

    # Check sheet for last saved timestamp
    try:
        sheet = get_alliance_sheet()
        rows = sheet.get_all_records()
        if not rows:
            print("⚠️ No entries in sheet; proceeding with snapshot.")
        else:
            # Assume last row is most recent
            last_time_str = rows[-1].get("TimeT", "")
            last_time = datetime.fromisoformat(last_time_str)

            if last_time.replace(minute=0, second=0, microsecond=0) == current_hour:
                print("⏭ Already saved snapshot this hour (based on sheet). Skipping.")
                return
    except Exception as e:
        print(f"⚠️ Failed to check sheet for last snapshot: {e}")

    try:
        totals = {res: 0 for res in [
            "money", "food", "gasoline", "munitions", "steel", "aluminum",
            "bauxite", "lead", "iron", "oil", "uranium", "coal", "num_cities"
        ]}
        processed_nations = 0
        failed = 0

        # Get market prices
        GRAPHQL_URL = f"https://api.politicsandwar.com/graphql?api_key={API_KEY}"
        prices_query = """
        {
          top_trade_info {
            resources {
              resource
              average_price
            }
          }
        }
        """
        try:
            resp = requests.post(GRAPHQL_URL, json={"query": prices_query}, headers={"Content-Type": "application/json"})
            resp.raise_for_status()
            prices = {item["resource"]: float(item["average_price"]) for item in resp.json()["data"]["top_trade_info"]["resources"]}
            print("✅ Resource prices fetched.")
        except Exception as e:
            print(f"❌ Error fetching prices: {e}")
            prices = {}

        seen_ids = set()

        for user_id, user_data in cached_users.items():
            nation_id = str(user_data.get("NationID", "")).strip()
            if not nation_id or nation_id in seen_ids:
                failed += 1
                continue

            seen_ids.add(nation_id)

            try:
                resources = get_resources(nation_id)
                (nation_name, num_cities, food, money, gasoline, munitions, steel,
                 aluminum, bauxite, lead, iron, oil, coal, uranium) = resources

                totals["money"] += money
                totals["food"] += food
                totals["gasoline"] += gasoline
                totals["munitions"] += munitions
                totals["steel"] += steel
                totals["aluminum"] += aluminum
                totals["bauxite"] += bauxite
                totals["lead"] += lead
                totals["iron"] += iron
                totals["oil"] += oil
                totals["coal"] += coal
                totals["uranium"] += uranium
                totals["num_cities"] += num_cities
                processed_nations += 1

                await asyncio.sleep(5)
            except Exception as e:
                failed += 1
                print(f"❌ Failed for nation {nation_id}: {e}")
                continue

        resource_values = {}
        total_wealth = totals["money"]

        for resource, amount in totals.items():
            if resource in ["money", "num_cities"]:
                continue
            price = prices.get(resource, 0)
            value = amount * price
            resource_values[resource] = value
            total_wealth += value

        timestamp = current_hour.isoformat()
        money_snapshots.append({"time": timestamp, "total": total_wealth})

        save_row = [timestamp, total_wealth, totals["money"]]
        ordered_resources = [
            "food", "gasoline", "munitions", "steel", "aluminum",
            "bauxite", "lead", "iron", "oil", "coal", "uranium"
        ]
        for res in ordered_resources:
            save_row.append(resource_values.get(res, 0))

        try:
            save_to_alliance_net(save_row)
            print(f"💾 Snapshot saved at {timestamp}: ${total_wealth:,.0f}")
        except Exception as e:
            print(f"❌ Failed to save snapshot: {e}")
    except Exception as e:
        print(f"Error: {e}")



@hourly_snapshot.before_loop
async def before_hourly():
    print("Waiting for bot to be ready before starting hourly snapshots...")
    await bot.wait_until_ready()

@bot.event
async def on_ready():
    bot.add_view(GrantView())   # Register persistent view
    bot.add_view(BlueGuy()) 
    load_sheet_data()
    load_registration_data()
    check_reminders.start()
    print("Starting hourly snapshot task...")
    if not hourly_snapshot.is_running():
        hourly_snapshot.start()
    if not process_auto_requests.is_running():
        process_auto_requests.start()
    if not hasattr(bot, "war_check_started"):  # Prevent multiple starts if on_ready fires again
        bot.war_check_started = True
        bot.loop.create_task(hourly_war_check())
        print("✅ hourly_war_check task started.")
    await bot.tree.sync()
    print(f"✅ Logged in as {bot.user}")

import asyncio
from discord.ext import tasks
from datetime import datetime, timedelta
import random

REMINDER_CHANNEL_ID = 1384922560902463519  # your target channel

@tasks.loop(hours=24)
async def check_reminders():
    await bot.wait_until_ready()
    now = datetime.utcnow()
    if not (4 <= now.hour < 6):
        return  # only run between 4–6 AM UTC

    sheet = get_bank_sheet()
    records = sheet.get_all_records()
    channel = bot.get_channel(REMINDER_CHANNEL_ID)
    if not channel:
        return

    for row in records:
        user_id = row["owner"]
        loan_date = row.get("loan_date")
        deposit_date = row.get("deposit_date")

        msg = None
        if loan_date:
            date = datetime.strptime(loan_date, "%Y-%m-%d")
            if now - date >= timedelta(days=7):
                msg = f"🔔 <@{user_id}> has an outstanding loan over 7 days old."

        if deposit_date:
            date = datetime.strptime(deposit_date, "%Y-%m-%d")
            if now - date >= timedelta(days=7):
                if msg:
                    msg += "\n"
                else:
                    msg = ""
                msg += f"🔔 <@{user_id}>'s safekeep balance has been held over 7 days."

        if msg:
            await asyncio.sleep(random.uniform(1, 3))  # prevent ratelimiting
            await channel.send(msg)


@bot.event
async def on_message(message):
    # Ignore all bots including yourself
    if message.author.bot:
        return

    # Debug print for any message
    #print(f"Message from {message.author} in guild {message.guild} content: {message.content}")

    # Your 1st logic: Respond to wilted rose in target guild excluding ignored users
    TARGET_GUILD_ID = 1186655069530243183
    IGNORED_USER_IDS = {1167879888892608663, 1148678095176474678}
    
    if message.guild and message.guild.id == TARGET_GUILD_ID:
        if message.author.id in IGNORED_USER_IDS:
            if "Money" in message.content:
                try:
                    reply = await message.reply(
                        "By copper’s clink and silver’s ring,\n"
                        "By debts unpaid and ledgers’ sting,\n"
                        "Barring, keeper of the fiscal flame,\n"
                        "I call thee now, in coin’s own name.\n"
                        "From vaults unseen and whispers charring,\n"
                        "Rise from the depths—I summon thee, <@722094493343416392>!"
                    )
                    await asyncio.sleep(10)
                    await reply.delete()
                except discord.Forbidden:
                    print("No permission to reply in this channel")
                except Exception as e:
                    print(f"Error replying: {e}")

            elif "Nuke" in message.content:
                try:
                    reply = await message.reply(
                        "From fires forged in honor’s name,\n"
                        "A force unleashed without a blame,\n"
                        "With steady hand and courage quick,\n"
                        "I summon forth the valiant <@1059576506684289034>."
                    )
                    await asyncio.sleep(10)
                    await reply.delete()
                except discord.Forbidden:
                    print("No permission to reply in this channel")
                except Exception as e:
                    print(f"Error replying: {e}")
    
            elif "Tax Evasion" in message.content:
                try:
                    reply = await message.reply(
                        "By loophole's path and audit's dread,\n"
                        "By offshore books and papers shed,\n"
                        "O Barring, ghost of gains concealed,\n"
                        "Whose wealth in shadows lies unrevealed,\n"
                        "Where ledgers burn and truths are scarring,\n"
                        "Come forth, unseen—I summon thee, <@722094493343416392>!"
                    )
                    await asyncio.sleep(10)
                    await reply.delete()
                except discord.Forbidden:
                    print("No permission to reply in this channel")
                except Exception as e:
                    print(f"Error replying: {e}")
            return

        if "🥀" in message.content:
            #print("🥀 detected, replying...")
            try:
                await message.reply("🥀")
                #print("Reply sent successfully")
            except discord.Forbidden:
                print("No permission to reply in this channel")
            except Exception as e:
                print(f"Error replying: {e}")
        elif "🌻" in message.content:
            try:
                await message.reply("https://tenor.com/LPuCUdzFpS.gif")
            except discord.Forbidden:
                print("No permission to reply in this channel")
            except Exception as e:
                print(f"Error replying: {e}")
        elif ":honest_reaction:" in message.content:
            try: 
                await message.reply("https://tenor.com/bMYJ6.gif")
            except discord.Forbidden:
                print("No permission to reply in this channel")
            except Exception as e:
                print(f"Error replying: {e}")
        elif "Money" in message.content:
            try:
                reply = await message.reply(
                    "By copper’s clink and silver’s ring,\n"
                    "By debts unpaid and ledgers’ sting,\n"
                    "Barring, keeper of the fiscal flame,\n"
                    "I call thee now, in coin’s own name.\n"
                    "From vaults unseen and whispers charring,\n"
                    "Rise from the depths—I summon thee, <@722094493343416392>!"
                )
                await asyncio.sleep(10)
                await reply.delete()
            except discord.Forbidden:
                print("No permission to reply in this channel")
            except Exception as e:
                print(f"Error replying: {e}")

        elif "Nuke" in message.content:
            try:
                reply = await message.reply(
                    "From fires forged in honor’s name,\n"
                    "A force unleashed without a blame,\n"
                    "With steady hand and courage quick,\n"
                    "I summon forth the valiant <@1059576506684289034>."
                )
                await asyncio.sleep(10)
                await reply.delete()
            except discord.Forbidden:
                print("No permission to reply in this channel")
            except Exception as e:
                print(f"Error replying: {e}")

        elif "Tax Evasion" in message.content:
            try:
                reply = await message.reply(
                    "By loophole's path and audit's dread,\n"
                    "By offshore books and papers shed,\n"
                    "O Barring, ghost of gains concealed,\n"
                    "Whose wealth in shadows lies unrevealed,\n"
                    "Where ledgers burn and truths are scarring,\n"
                    "Come forth, unseen—I summon thee, <@722094493343416392>!"
                )
                await asyncio.sleep(10)
                await reply.delete()
            except discord.Forbidden:
                print("No permission to reply in this channel")
            except Exception as e:
                print(f"Error replying: {e}")


            

    # Your 2nd logic: Handle direct messages to the bot
    if message.guild is None:  # DM channel
        default_reply = "Thanks for your message! We'll get back to you soon."

        last_bot_msg = None
        async for msg in message.channel.history(limit=20, before=message.created_at):
            if msg.author == bot.user:
                last_bot_msg = msg.content
                break

        if last_bot_msg != default_reply:
            log_channel_id = 1262301979242401822
            log_channel = bot.get_channel(log_channel_id)
            if log_channel:
                embed = discord.Embed(
                    title="New DM received",
                    description=(
                        f"**From:** {message.author} (`{message.author.id}`)\n"
                        f"**User message:**\n{message.content}\n\n"
                        f"**Last bot message to user:**\n{last_bot_msg or 'None'}"
                    ),
                    color=discord.Color.blue()
                )
                await log_channel.send(embed=embed)

        await message.channel.send(default_reply)

    # Make sure commands still work
    await bot.process_commands(message)


@bot.tree.command(name="register", description="Register your Nation ID")
@app_commands.describe(nation_id="Your Nation ID (numbers only, e.g., 365325)")
async def register(interaction: discord.Interaction, nation_id: str):
    await interaction.response.defer()

    async def is_banker(interaction):
        return (
        any(role.name == "Member" for role in interaction.user.roles)
            or str(interaction.user.id) == "1148678095176474678"
        )

    if not await is_banker(interaction):
        await interaction.followup.send("❌ You need to be a Member to register yourself.")
        return

    if not nation_id.isdigit():
        await interaction.followup.send("❌ Please enter only the Nation ID number, not a link.")
        return

    url = f"https://politicsandwar.com/nation/id={nation_id}"
    session = requests.Session()
    response = session.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')

    discord_label = soup.find(string="Discord Username:")
    if not discord_label:
        await interaction.followup.send("❌ Invalid Nation ID or the nation has no Discord username listed.")
        return

    try:
        nation_discord_username = discord_label.parent.find_next_sibling("td").text.strip().lower()
    except Exception:
        await interaction.followup.send("❌ Could not parse nation information.")
        return

    user_discord_username = interaction.user.name.strip().lower()
    user_id = str(interaction.user.id)
    nation_id_str = str(nation_id).strip()

    if user_discord_username != "sumnor":
        if nation_discord_username != user_discord_username:
            await interaction.followup.send(
                f"❌ Username mismatch.\nNation lists: `{nation_discord_username}`\nYour Discord: `{user_discord_username}`"
            )
            return

    global cached_users

    for uid, data in cached_users.items():
        if user_discord_username != "sumnor":
            if uid == user_id:
                await interaction.followup.send("❌ This Discord ID is already registered.")
                return
            if data['DiscordUsername'] == user_discord_username:
                await interaction.followup.send("❌ This Discord username is already registered.")
                return
            if data['NationID'] == nation_id_str:
                await interaction.followup.send("❌ This Nation ID is already registered.")
                return

    try:
        sheet = get_sheet()
        sheet.append_row([interaction.user.name, user_id, nation_id])
    except Exception as e:
        await interaction.followup.send(f"❌ Failed to write registration: {e}")
        return

    load_sheet_data()
    await interaction.followup.send("✅ You're registered successfully!")

from datetime import datetime
from typing import Dict

import discord
from discord.ext import commands
from discord import app_commands
import random
import asyncio
from typing import Dict, List

blackjack_tables: Dict[int, Dict] = {}

CARD_VALUES = {
    '2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9,
    '10': 10, 'J': 10, 'Q': 10, 'K': 10, 'A': 11
}

SUITS = ['♥', '♦', '♣', '♠']
RANKS = list(CARD_VALUES.keys())

def draw_card():
    return f"{random.choice(RANKS)}{random.choice(SUITS)}"

def calculate_hand(cards):
    value = 0
    aces = 0
    for card in cards:
        rank = card[:-1]
        value += CARD_VALUES[rank]
        if rank == 'A':
            aces += 1
    while value > 21 and aces:
        value -= 10
        aces -= 1
    return value

class HitStandView(discord.ui.View):
    def __init__(self, player_id, table_id):
        super().__init__(timeout=60)
        self.player_id = player_id
        self.table_id = table_id

    @discord.ui.button(label="Hit", style=discord.ButtonStyle.primary)
    async def hit(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.player_id:
            await interaction.response.send_message("Not your hand!", ephemeral=True)
            return
        player = blackjack_tables[self.table_id]['players'][self.player_id]
        card = draw_card()
        player['cards'].append(card)
        hand_value = calculate_hand(player['cards'])

        embed = discord.Embed(title="\U0001F0A1 Your Hand", description=f"Cards: {', '.join(player['cards'])}\nTotal: {hand_value}", color=discord.Color.green())
        if hand_value > 21:
            embed.color = discord.Color.red()
            embed.set_footer(text="Bust!")
            player['stood'] = True
            await check_game_over(self.table_id)
            self.stop()
        await interaction.response.edit_message(embed=embed, view=None if hand_value > 21 else self)

    @discord.ui.button(label="Stand", style=discord.ButtonStyle.secondary)
    async def stand(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.player_id:
            await interaction.response.send_message("Not your hand!", ephemeral=True)
            return
        blackjack_tables[self.table_id]['players'][self.player_id]['stood'] = True
        await interaction.response.send_message("You stood.", ephemeral=True)
        await check_game_over(self.table_id)
        self.stop()

    def stop_view(self):
        self.stop()

async def check_game_over(table_id):
    table = blackjack_tables[table_id]
    if all(p['stood'] or calculate_hand(p['cards']) > 21 for p in table['players'].values()):
        if table.get('round_resolving'):
            return  # Already resolving, skip
        table['round_resolving'] = True
        await asyncio.sleep(2)
        await resolve_round(table_id)
        table['round_resolving'] = False

@bot.tree.command(name="blackjack", description="Start a blackjack table")
async def blackjack(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    thread = await interaction.channel.create_thread(name=f"Blackjack Table - {interaction.user.display_name}", type=discord.ChannelType.private_thread)
    blackjack_tables[thread.id] = {
        'host': interaction.user.id,
        'players': {
            interaction.user.id: {'user': interaction.user, 'cards': [], 'stood': False, 'bet': None, 'view': None}
        },
        'started': False,
        'round_resolving': False
    }
    await interaction.followup.send(f"\U0001F3B2 Blackjack table created in {thread.mention}! Use `/join_blackjack` to join, then `/bet_blackjack` to place your bet.", ephemeral=True)

@bot.tree.command(name="join_blackjack", description="Join a blackjack thread")
async def join_blackjack(interaction: discord.Interaction):
    if not isinstance(interaction.channel, discord.Thread):
        return await interaction.response.send_message("This command must be used inside a blackjack thread.", ephemeral=True)
    table = blackjack_tables.get(interaction.channel.id)
    if not table or table['started']:
        return await interaction.response.send_message("Can't join this table.", ephemeral=True)
    if interaction.user.id in table['players']:
        return await interaction.response.send_message("You're already at this table.", ephemeral=True)
    table['players'][interaction.user.id] = {'user': interaction.user, 'cards': [], 'stood': False, 'bet': None, 'view': None}
    await interaction.response.send_message("You joined the blackjack table. Now use `/bet_blackjack` to place your bet.", ephemeral=True)

@bot.tree.command(name="bet_blackjack", description="Place your blackjack bet")
@app_commands.describe(bet="Your bet amount")
async def bet_blackjack(interaction: discord.Interaction, bet: int):
    if not isinstance(interaction.channel, discord.Thread):
        return await interaction.response.send_message("This command must be used inside a blackjack thread.", ephemeral=True)
    table = blackjack_tables.get(interaction.channel.id)
    if not table or interaction.user.id not in table['players']:
        return await interaction.response.send_message("You're not at this table.", ephemeral=True)
    player = table['players'][interaction.user.id]
    if player['bet'] is not None:
        return await interaction.response.send_message("You've already placed a bet.", ephemeral=True)
    player['bet'] = bet
    await interaction.response.send_message(f"Bet of ${bet} accepted.", ephemeral=True)

@bot.tree.command(name="start_blackjack_round", description="Start a new round (host only)")
async def start_blackjack_round(interaction: discord.Interaction):
    if not isinstance(interaction.channel, discord.Thread):
        return await interaction.response.send_message("Use this inside a blackjack thread.", ephemeral=True)

    table = blackjack_tables.get(interaction.channel.id)
    if not table:
        return await interaction.response.send_message("No active blackjack table here.", ephemeral=True)

    if interaction.user.id != table['host']:
        return await interaction.response.send_message("Only the table host can start the round.", ephemeral=True)

    if table['started']:
        return await interaction.response.send_message("A round is already in progress.", ephemeral=True)

    if not all(p['bet'] is not None for p in table['players'].values()):
        return await interaction.response.send_message("Not all players have placed their bets.", ephemeral=True)

    await interaction.response.send_message("✅ Starting the round...", ephemeral=True)
    await start_game(interaction.channel, table)

async def start_game(channel, table):
    table['started'] = True
    for player_id, player_data in list(table['players'].items()):
        player_data['cards'] = [draw_card(), draw_card()]
        player_data['stood'] = False
        hand_value = calculate_hand(player_data['cards'])
        embed = discord.Embed(title="\U0001F0A1 Your Hand", description=f"Cards: {', '.join(player_data['cards'])}\nTotal: {hand_value}", color=discord.Color.green())
        view = HitStandView(player_id, channel.id)
        player_data['view'] = view
        try:
            await player_data['user'].send(embed=embed, view=view)
        except discord.Forbidden:
            await channel.send(f"Couldn't DM {player_data['user'].mention}, removing from game.")
            del table['players'][player_id]

    await channel.send("Blackjack started! Players have been DMed their cards.")

async def resolve_round(table_id):
    table = blackjack_tables[table_id]
    total_pot = sum(pdata['bet'] for pdata in table['players'].values() if pdata['bet'] is not None)
    
    # Find best score <= 21
    best_score = 0
    winners = []
    for pdata in table['players'].values():
        score = calculate_hand(pdata['cards'])
        if score <= 21:
            if score > best_score:
                best_score = score
                winners = [pdata]
            elif score == best_score:
                winners.append(pdata)

    channel = bot.get_channel(table_id)
    if not winners or best_score == 0:
        await channel.send("💥 All players busted or timed out. No winners this round.")
    else:
        # Calculate payout per winner (split pot)
        payout_per_winner = total_pot // len(winners)  # integer division for whole number payout
        
        # Build winnings message with amounts
        winner_mentions = []
        for winner in winners:
            # Here you should implement adding payout_per_winner to user's balance (if you have one)
            winner_mentions.append(f"{winner['user'].mention} (${payout_per_winner})")

        winners_text = ", ".join(winner_mentions)
        await channel.send(f"🏆 Round over! Winner(s): {winners_text} with {best_score} points! Total pot: ${total_pot} split evenly.")

    # Reset player states but keep players (don't remove)
    for pdata in table['players'].values():
        pdata['cards'] = []
        pdata['stood'] = False
        pdata['bet'] = None

    table['started'] = False
    table.pop('betting_started', None)
    await channel.send("🌀 Round complete. Players may now place new bets with `/bet_blackjack` or new users can `/join_blackjack`.")


import discord
from discord.ext import commands
from discord import app_commands
import random
import asyncio
from typing import Dict, List

poker_tables: Dict[int, Dict] = {}

class PokerPlayer:
    def __init__(self, user: discord.User):
        self.user = user
        self.hand = []
        self.folded = False
        self.balance = 0
        self.current_bet = 0

class PokerView(discord.ui.View):
    def __init__(self, table_id, player_id):
        super().__init__(timeout=None)
        self.table_id = table_id
        self.player_id = player_id

    @discord.ui.button(label="Fold", style=discord.ButtonStyle.danger)
    async def fold(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.player_id:
            await interaction.response.send_message("Not your turn!", ephemeral=True)
            return
        table = poker_tables[self.table_id]
        table['players'][self.player_id].folded = True
        await interaction.response.send_message("You folded.", ephemeral=True)
        await next_turn(self.table_id)

    @discord.ui.button(label="Check/Call", style=discord.ButtonStyle.secondary)
    async def call(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.player_id:
            await interaction.response.send_message("Not your turn!", ephemeral=True)
            return
        table = poker_tables[self.table_id]
        player = table['players'][self.player_id]
        call_amount = table['current_bet'] - player.current_bet
        player.balance -= call_amount
        table['pot'] += call_amount
        player.current_bet = table['current_bet']
        await interaction.response.send_message(f"You called ${call_amount}.", ephemeral=True)
        await next_turn(self.table_id)

    @discord.ui.button(label="Raise $10", style=discord.ButtonStyle.primary)
    async def raise_bet(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.player_id:
            await interaction.response.send_message("Not your turn!", ephemeral=True)
            return
        table = poker_tables[self.table_id]
        player = table['players'][self.player_id]
        raise_amount = 10
        total_bet = table['current_bet'] + raise_amount
        to_call = total_bet - player.current_bet
        player.balance -= to_call
        table['pot'] += to_call
        player.current_bet = total_bet
        table['current_bet'] = total_bet
        table['raise_by'] = self.player_id
        await interaction.response.send_message(f"You raised ${raise_amount}. Total bet is now ${total_bet}.", ephemeral=True)
        await next_turn(self.table_id)

@bot.tree.command(name="poker", description="Start a poker table")
async def poker(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    thread = await interaction.channel.create_thread(name=f"Poker Table - {interaction.user.display_name}", type=discord.ChannelType.private_thread)
    poker_tables[thread.id] = {
        'host': interaction.user.id,
        'players': {},
        'pot': 0,
        'current_bet': 0,
        'raise_by': None,
        'turn_order': [],
        'turn_index': 0,
        'community': [],
        'round_stage': 'preflop',
        'deck': []
    }
    await interaction.followup.send(f"🃏 Poker table created in {thread.mention}! Use `/join_poker` and `/buyin_poker`.", ephemeral=True)

@bot.tree.command(name="join_poker", description="Join a poker thread")
async def join_poker(interaction: discord.Interaction):
    if not isinstance(interaction.channel, discord.Thread):
        return await interaction.response.send_message("Use this in a poker thread.", ephemeral=True)
    table = poker_tables.get(interaction.channel.id)
    if not table:
        return await interaction.response.send_message("No active table.", ephemeral=True)
    if interaction.user.id in table['players']:
        return await interaction.response.send_message("Already joined.", ephemeral=True)
    table['players'][interaction.user.id] = PokerPlayer(interaction.user)
    await interaction.response.send_message("Joined poker table! Use `/buyin_poker`.", ephemeral=True)

@bot.tree.command(name="buyin_poker", description="Add funds to your poker account")
@app_commands.describe(amount="Amount to deposit")
async def buyin_poker(interaction: discord.Interaction, amount: int):
    if not isinstance(interaction.channel, discord.Thread):
        return await interaction.response.send_message("Use this in a poker thread.", ephemeral=True)
    table = poker_tables.get(interaction.channel.id)
    if not table or interaction.user.id not in table['players']:
        return await interaction.response.send_message("Not at this table.", ephemeral=True)
    player = table['players'][interaction.user.id]
    player.balance += amount
    await interaction.response.send_message(f"Added ${amount} to your poker balance. Total: ${player.balance}.", ephemeral=True)

@bot.tree.command(name="start_poker_round", description="Start a poker round (host only)")
async def start_poker_round(interaction: discord.Interaction):
    await interaction.response.defer()
    if not isinstance(interaction.channel, discord.Thread):
        return await interaction.followup.send("Use this in a poker thread.", ephemeral=True)

    table = poker_tables.get(interaction.channel.id)
    if not table or interaction.user.id != table['host']:
        return await interaction.followup.send("Only the host can start a round.", ephemeral=True)

    table['pot'] = 0
    table['current_bet'] = 0
    table['raise_by'] = None
    table['community'] = []
    table['deck'] = [f"{r}{s}" for r in "23456789TJQKA" for s in "♠♥♦♣"]
    random.shuffle(table['deck'])
    table['round_stage'] = 'preflop'
    table['turn_order'] = [pid for pid, p in table['players'].items() if p.balance > 0]
    table['turn_index'] = 0

    for pid in table['turn_order']:
        player = table['players'][pid]
        player.folded = False
        player.current_bet = 0
        player.hand = [table['deck'].pop(), table['deck'].pop()]

    for pid in table['turn_order']:
        try:
            await table['players'][pid].user.send(f"🃏 Your hand: {' '.join(table['players'][pid].hand)}")
        except discord.Forbidden:
            await interaction.channel.send(f"❗ Couldn't DM {table['players'][pid].user.mention}", delete_after=10)

    await next_turn(interaction.channel.id)

async def next_turn(table_id):
    table = poker_tables[table_id]
    channel = bot.get_channel(table_id)
    active_players = [p for pid, p in table['players'].items() if pid in table['turn_order'] and not p.folded and p.balance > 0]

    if len(active_players) <= 1:
        await end_round(table_id, forced_winner=active_players[0] if active_players else None)
        return

    if all(p.current_bet == table['current_bet'] for p in active_players):
        await reveal_community_cards(table_id)
        return

    while True:
        if table['turn_index'] >= len(table['turn_order']):
            table['turn_index'] = 0

        pid = table['turn_order'][table['turn_index']]
        table['turn_index'] += 1
        player = table['players'][pid]

        if player.folded or player.balance <= 0:
            continue

        view = PokerView(table_id, pid)
        message = await channel.send(
            f"🎯 {player.user.mention}, it's your turn.\n"
            f"Pot: ${table['pot']} | Your Balance: ${player.balance} | Current Bet: ${table['current_bet']}",
            view=view
        )

        def check(inter: discord.Interaction):
            return inter.user.id == pid and inter.message.id == message.id

        try:
            await bot.wait_for("interaction", check=check, timeout=60)
        except asyncio.TimeoutError:
            player.folded = True
            await channel.send(f"⏰ {player.user.mention} took too long and folded.")

        break

async def reveal_community_cards(table_id):
    table = poker_tables[table_id]
    channel = bot.get_channel(table_id)

    if table['round_stage'] == 'preflop':
        table['community'] = [table['deck'].pop() for _ in range(3)]
        table['round_stage'] = 'flop'
        await channel.send(f"📢 **Flop**: {' '.join(table['community'])}")
    elif table['round_stage'] == 'flop':
        table['community'].append(table['deck'].pop())
        table['round_stage'] = 'turn'
        await channel.send(f"📢 **Turn**: {' '.join(table['community'])}")
    elif table['round_stage'] == 'turn':
        table['community'].append(table['deck'].pop())
        table['round_stage'] = 'river'
        await channel.send(f"📢 **River**: {' '.join(table['community'])}")
    elif table['round_stage'] == 'river':
        table['round_stage'] = 'showdown'
        await channel.send("🏁 All cards revealed. Showdown begins!")
        await end_round(table_id)
        return

    table['current_bet'] = 0
    table['raise_by'] = None
    for pid in table['turn_order']:
        table['players'][pid].current_bet = 0

    await next_turn(table_id)

async def end_round(table_id, forced_winner=None):
    table = poker_tables[table_id]
    players = table['players']
    players_in_game = [p for p in players.values() if not p.folded]
    actions = []

    if forced_winner:
        winner = forced_winner
    elif not players_in_game:
        winner = None
    else:
        winner = players_in_game[0]  # Replace with proper evaluation

    if winner:
        winner.balance += table['pot']
        result_msg = f"🏆 Winner: {winner.user.display_name} wins ${table['pot']}!"
    else:
        result_msg = "❌ All players folded. No winner."

    for player in players.values():
        if player.folded:
            actions.append(f"{player.user.display_name}: Folded")
        else:
            actions.append(
                f"{player.user.display_name}: Called ${player.current_bet}, Remaining Balance: ${player.balance}"
            )

    action_summary = "\n".join(actions)
    channel = bot.get_channel(table_id)
    await channel.send(f"🎯 Round Results:\n{result_msg}\n\n📝 Actions:\n{action_summary}")
    await channel.send("🌀 Round reset. Use `/start_poker_round` for the next round.")

@bot.tree.command(name="open_account", description="Request to open an INTRA personal account")
@app_commands.describe(nation_id="Your own id, not the AA one")
async def open_account(interaction: discord.Interaction, nation_id: str):
    await interaction.response.defer()
    user_id = str(interaction.user.id)
    sheet = get_bank_sheet()
    records = sheet.get_all_records()

    user_rows = [r for r in records if str(r["owner"]) == user_id]
    has_personal = any(not str(r["aa_name"]).strip() for r in user_rows)

    if has_personal:
        return await interaction.followup.send("❌ You already have a personal account.")

    # Pass nation_id to the approval view
    view = AccountApprovalView(user_id=user_id, nation_id=nation_id, aa_name=None)
    await interaction.followup.send(
        f"📝 <@{user_id}> has requested to open an INTRA personal account.\nA staff member must approve below:",
        view=view
    )


@bot.tree.command(name="open_account_aa", description="Request to create a private AA account")
@app_commands.describe(aa_name="Your AA account name (must be unique)")
@app_commands.describe(nation_id="Your own id, not the AA one")
async def open_account_aa(interaction: discord.Interaction, aa_name: str, nation_id: str):
    await interaction.response.defer()
    user_id = str(interaction.user.id)
    sheet = get_bank_sheet()
    all_records = sheet.get_all_records()

    global_names = [str(r["aa_name"]).lower() for r in all_records if r["aa_name"]]
    if aa_name.lower() in global_names:
        return await interaction.followup.send("❌ That name is already taken.")

    # Pass nation_id and aa_name to approval view
    view = AccountApprovalView(user_id=user_id, aa_name=aa_name, nation_id=nation_id)
    await interaction.followup.send(
        f"📝 <@{user_id}> requested to create AA `{aa_name}`. Staff must approve:",
        view=view
    )

@bot.tree.command(name="trade_search", description="Search for a person to trade with")
@app_commands.describe(
    receive_trade="Select if you want to Trade or Receive",
    uranium="Amount of uranium requested",
    coal="Amount of coal requested",
    oil="Amount of oil requested",
    bauxite="Amount of bauxite requested",
    lead="Amount of lead requested",
    iron="Amount of iron requested",
    steel="Amount of steel requested",
    aluminum="Amount of aluminum requested",
    gasoline="Amount of gasoline requested",
    money="Amount of money requested",
    food="Amount of food requested",
    munitions="Amount of munitions requested"
)
@app_commands.choices(receive_trade=[
    app_commands.Choice(name="Trade", value="trade"),
    app_commands.Choice(name="Receive", value="receive")
])
async def trade_search(
    interaction: discord.Interaction,
    receive_trade: app_commands.Choice[str],
    uranium: str = "0",
    coal: str = "0",
    oil: str = "0",
    bauxite: str = "0",
    lead: str = "0",
    iron: str = "0",
    steel: str = "0",
    aluminum: str = "0",
    gasoline: str = "0",
    money: str = "0",
    food: str = "0",
    munitions: str = "0",
):
    await interaction.response.defer()

    discord_name = str(interaction.user)

    raw_inputs = {
        "Uranium": uranium,
        "Coal": coal,
        "Oil": oil,
        "Bauxite": bauxite,
        "Lead": lead,
        "Iron": iron,
        "Steel": steel,
        "Aluminum": aluminum,
        "Gasoline": gasoline,
        "Money": money,
        "Food": food,
        "Munitions": munitions,
    }
    resources = {k: int(v) if v.isdigit() else 0 for k, v in raw_inputs.items()}
    requested = {k: v for k, v in resources.items() if v > 0}

    if not requested:
        return await interaction.followup.send("❌ You must request at least one resource.")

    description = "\n".join(f"{k}: {v:,}".replace(",", ".") for k, v in requested.items())
    embed = discord.Embed(
        title="📦 Trade Request",
        color=discord.Color.blurple(),
        description=(
            f"**{discord_name}** wants to **{receive_trade.name.lower()}** the following:\n\n"
            f"{description}\n\n"
            f"**⚠️ INTRA does not mediate or assosiate in trades between nations**"
        )
    )
    embed.set_footer(text="Brought to you by INTRA")

    # Send message and wait to get the message object
    message = await interaction.followup.send(embed=embed, wait=True)

    # Create the view and assign it to the sent message
    view = TradeButton(interaction.user, requested, message)
    await message.edit(view=view)

@bot.tree.command(name="take_loan_aa", description="Take a loan from your AA")
@app_commands.describe(aa_name="Your AA account", amount="How much to borrow")
async def take_loan_aa(interaction, aa_name: str, amount: int):
    await interaction.response.defer()
    owner = str(interaction.user.id)
    sheet, idx, row = get_account_row(owner, aa_name)
    if not row:
        return await interaction.followup.send(f"❌ No account `{aa_name}`.")
    if amount <= 0:
        return await interaction.followup.send("❌ Must be positive.")

    loans = int(row["loans"])
    trust = float(row["trust"])
    new_loans = loans + amount

    append_history(sheet, idx, 7, {"amount": amount, "date": datetime.utcnow().isoformat()})
    update_weekly_payback(sheet, idx, new_loans, trust)
    update_weeks_since(sheet, idx, json.loads(sheet.cell(idx,7).value))
    sheet.update_cell(idx, 4, new_loans)

    await interaction.followup.send(
        f"✅ Loaned ${amount}. Total debt: ${new_loans}. Weekly pay: ${sheet.cell(idx,9).value}"
    )


import json
from datetime import datetime
import discord
from discord import app_commands
import requests
from dateutil.parser import isoparse
from dateutil.tz import UTC

@bot.tree.command(name="deposit_aa", description="Deposit into your AA")
@app_commands.describe(aa_name="Your AA", amount="Amount to deposit")
async def deposit_aa(interaction: discord.Interaction, aa_name: str, amount: int):
    await interaction.response.defer()

    if amount <= 0:
        return await interaction.followup.send("❌ Must be positive.")

    user_id = str(interaction.user.id)
    sheet, idx, row = get_account_row(user_id, aa_name)
    if not row:
        return await interaction.followup.send(f"❌ No account `{aa_name}` or you don’t have access.")

    last_deposit_str = row.get("last_deposit") or "2000-01-01T00:00:00Z"
    try:
        last_deposit = (
            isoparse(last_deposit_str)
            .replace(second=0, microsecond=0)
            .astimezone(UTC)
        )
    except Exception:
        last_deposit = datetime(2000, 1, 1, tzinfo=UTC)

    API_KEY_PERS = "7f07d02e27f57fdba1f9"
    GRAPHQL_URL = f"https://api.politicsandwar.com/graphql?api_key={API_KEY_PERS}"

    # Get Neprito's nation ID with error handling
    nation_id_query = """
    query {
      nations(nation_name: "Neprito") {
        data {
          id
        }
      }
    }
    """
    try:
        res = requests.post(GRAPHQL_URL, json={"query": nation_id_query}).json()
        neprito_data = res["data"]["nations"]["data"]
        if not neprito_data:
            return await interaction.followup.send("❌ Could not find nation 'Neprito'.")
        neprito_id = int(neprito_data[0]["id"])
    except Exception as e:
        return await interaction.followup.send(f"❌ Error fetching Neprito ID: {e}")

    # Get recent trades for Neprito
    trade_query = """
    query {
      nations(nation_name: "Neprito") {
        data {
          trades(offer_resource: "food") {
            id
            receiver_id
            offer_resource
            offer_amount
            price
            accepted
            date
          }
        }
      }
    }
    """
    try:
        response = requests.post(GRAPHQL_URL, json={"query": trade_query})
        trades = response.json()["data"]["nations"]["data"][0]["trades"]
    except Exception as e:
        return await interaction.followup.send(f"❌ Error fetching trades: {e}")

    valid_trade = None
    for trade in trades[:10]:
        try:
            trade_date = (
                isoparse(trade["date"])
                .replace(second=0, microsecond=0)
                .astimezone(UTC)
            )
        except Exception:
            continue

        if (
            trade["accepted"]
            and int(trade["receiver_id"]) == neprito_id
            and trade["offer_amount"] == 1
            and int(trade["price"]) == amount
            and trade_date > last_deposit
        ):
            valid_trade = trade
            break

    if not valid_trade:
        return await interaction.followup.send("❌ No valid 1-food trade found since your last deposit.")

    # Process deposit
    loans = int(row["loans"])
    money = int(row["money"])
    repay = min(amount, loans)
    add = amount - repay
    new_loans = loans - repay
    new_money = money + add

    # Update the sheet cells
    try:
        sheet.update_cell(idx, 4, new_loans)  # loans column index
        sheet.update_cell(idx, 3, new_money)  # money column index
        # Save last_deposit as ISO8601 with Z
        new_date_str = datetime.utcnow().replace(second=0, microsecond=0, tzinfo=UTC).isoformat().replace("+00:00", "Z")
        sheet.update_cell(idx, 7, new_date_str)  # last_deposit column index

        append_history(sheet, idx, 8, {"amount": amount, "date": new_date_str})
        update_weekly_payback(sheet, idx, new_loans, float(row["trust"]))
        update_weeks_since(sheet, idx, json.loads(sheet.cell(idx, 8).value))
    except Exception as e:
        return await interaction.followup.send(f"❌ Failed to update sheet: {e}")

    await interaction.followup.send(
        f"💵 Deposited ${amount} via trade ID {valid_trade['id']}.\n"
        f"Debt ${new_loans}. Balance ${new_money}. Weekly pay: ${sheet.cell(idx, 9).value}"
    )




@bot.tree.command(name="balance_aa", description="Show AA balances")
@app_commands.describe(aa_name="Your AA account")
async def balance_aa(interaction, aa_name: str):
    await interaction.response.defer()
    user_id = str(interaction.user.id)
    sheet, idx, row = get_account_row(user_id, aa_name)
    if not row:
        return await interaction.followup.send(f"❌ No account `{aa_name}` or you don’t have access.")

    loans, money, trading = int(row["loans"]), int(row["money"]), int(row["trading"])
    weekly, weeks = float(row["loan_weekly"]), int(row["loan_weeks_since"])
    embed = discord.Embed(
        title="**DS**",
        colour=discord.Colour.dark_gold(),
        description=f"**{aa_name}**\nMoney: ${money}\nLoans: ${loans}  Weekly Pay: ${weekly:.2f}\nWeeks Since Last Payment: {weeks}\nTrading: ${trading}"
    )
    embed.set_footer(text="Brought to you by INTRA")
    await interaction.followup.send(embed=embed)


@bot.tree.command(name="trust_aa", description="Set trust rate on an AA (Staff only)")
@app_commands.describe(aa_name="AA account name", rate="Monthly trust rate (e.g., 0.05)")
async def trust_aa(interaction: discord.Interaction, aa_name: str, rate: float):
    await interaction.response.defer(ephemeral=True)
    if not any(role.name == "Staff" for role in interaction.user.roles):
        return await interaction.followup.send("🚫 Staff only.", ephemeral=True)
    user_id = str(interaction.user.id)
    sheet, idx, row = get_account_row(user_id, aa_name)
    if not row:
        return await interaction.followup.send(f"❌ No account `{aa_name}` or you don’t have access.")

    sheet.update_cell(idx, 6, rate)
    await interaction.followup.send(f"✅ Trust for `{aa_name}` set to {rate}.")

@bot.tree.command(name="grant_access", description="Grant someone access to your AA account")
@app_commands.describe(aa_name="Name of your AA account", user="User to grant access to")
async def grant_access(interaction: discord.Interaction, aa_name: str, user: discord.Member):
    await interaction.response.defer()
    owner_id = str(interaction.user.id)

    sheet = get_bank_sheet()
    records = sheet.get_all_records()
    for idx, row in enumerate(records, start=2):
        if str(row["owner"]) == owner_id and str(row["aa_name"]).lower() == aa_name.lower():
            try:
                members = json.loads(row.get("members", "[]"))
            except:
                members = []

            if str(user.id) in members:
                return await interaction.followup.send("⚠️ That user already has access.")

            members.append(str(user.id))
            sheet.update_cell(idx, 11, json.dumps(members))  # assuming column 11 = members

            role = discord.utils.get(interaction.guild.roles, name="AA Account Owner")
            if role and not user.get_role(role.id):
                await user.add_roles(role, reason="Granted access to AA")

            return await interaction.followup.send(f"✅ <@{user.id}> has been granted access to `{aa_name}`.")

    return await interaction.followup.send("❌ You don’t own that AA.")

@bot.tree.command(name="revoke_access", description="Revoke a user's access to your AA")
@app_commands.describe(aa_name="Name of your AA account", user="User to remove access from")
async def revoke_access(interaction: discord.Interaction, aa_name: str, user: discord.Member):
    await interaction.response.defer()
    owner_id = str(interaction.user.id)

    sheet = get_bank_sheet()
    records = sheet.get_all_records()
    for idx, row in enumerate(records, start=2):
        if str(row["owner"]) == owner_id and str(row["aa_name"]).lower() == aa_name.lower():
            try:
                members = json.loads(row.get("members", "[]"))
            except:
                members = []

            if str(user.id) not in members:
                return await interaction.followup.send("⚠️ That user doesn’t have access.")

            members.remove(str(user.id))
            sheet.update_cell(idx, 11, json.dumps(members))

            role = discord.utils.get(interaction.guild.roles, name="AA Account Owner")
            if role and user.get_role(role.id):
                await user.remove_roles(role, reason="Access to AA revoked")

            return await interaction.followup.send(f"🚫 <@{user.id}>'s access to `{aa_name}` has been revoked.")

    return await interaction.followup.send("❌ You don’t own that AA.")

@bot.tree.command(name="balance", description="Check your balance")
async def balance(interaction: discord.Interaction):
    await interaction.response.defer()
    sheet, row_index, row = get_user_row(interaction.user.id)
    if not row:
        return await interaction.followup.send("❌ You don't have an account.")
    money = row.get("money", "0")
    loans = row.get("loans", "0")
    trust = row.get("trust", "0")
    balance_message = (
        f"💰 Balance: ${money}\n"
        f"💸 Loans: ${loans}\n"
        f"🤝 Trust Level: ${trust}"
    )
    embed = discord.Embed(
        title=f"Your Balance",
        colour=discord.Colour.dark_gold(),
        description=balance_message
    )
    await interaction.followup.send(
        embed=embed
    )


@bot.tree.command(name="take_loan", description="Take out a loan")
@app_commands.describe(amount="How much to borrow")
async def take_loan(interaction: discord.Interaction, amount: int):
    await interaction.response.defer()
    if amount <= 0:
        return await interaction.followup.send("❌ Amount must be positive.")
    sheet, row_index, row = get_user_row(interaction.user.id)
    if not row:
        return await interaction.followup.send("❌ You don't have an account.")
    current_loans = int(row["loans"])
    trust = int(row.get("trust", 0))

    if current_loans + amount > trust:
        return await interaction.followup.send(
            f"🚫 Loan exceeds your trust limit of ${trust}. You currently owe ${current_loans}."
        )

    new_loan = current_loans + amount
    sheet.update_cell(row_index, 4, new_loan)
    sheet.update_cell(row_index, 7, datetime.utcnow().strftime("%Y-%m-%d"))
    await interaction.followup.send(f"✅ Loan of ${amount} taken. Total debt: ${new_loan}")


import json
from datetime import datetime
import discord
from discord import app_commands
import requests
from dateutil.parser import isoparse
from dateutil.tz import UTC

@bot.tree.command(name="deposit", description="Deposit into safekeep")
@app_commands.describe(amount="How much to deposit")
async def deposit(interaction: discord.Interaction, amount: int):
    await interaction.response.defer()

    if amount <= 0:
        return await interaction.followup.send("❌ Amount must be positive.")

    # Get user row (implement this to get user's row and index from your sheet)
    sheet, row_index, row = get_user_row(interaction.user.id)
    if not row:
        return await interaction.followup.send("❌ You don't have an account.")

    date_sheet_str = row.get("deposit_history", None)

    try:
        # Parse sheet date, set seconds and microseconds to 0, ensure UTC aware
        sheet_date = (
            isoparse(date_sheet_str)
            .replace(second=0, microsecond=0)
            .astimezone(UTC)
            if date_sheet_str else None
        )
    except Exception:
        sheet_date = None

    # API setup
    API_KEY_PERS = "7f07d02e27f57fdba1f9"
    GRAPHQL_URL = f"https://api.politicsandwar.com/graphql?api_key={API_KEY_PERS}"

    # Get Neprito's nation ID
    nation_id_query = """
    query {
      nations(nation_name: "Neprito") {
        data {
          id
        }
      }
    }
    """
    try:
        res = requests.post(GRAPHQL_URL, json={"query": nation_id_query}).json()
        neprito_data = res["data"]["nations"]["data"]
        if not neprito_data:
            return await interaction.followup.send("❌ Could not find nation 'Neprito'.")
        neprito_id = int(neprito_data[0]["id"])
    except Exception as e:
        return await interaction.followup.send(f"❌ Error fetching Neprito ID: {e}")

    # Get last trades for Neprito
    trade_query = """
    query {
      nations(nation_name: "Neprito") {
        data {
          trades(offer_resource: "food") {
            id
            sender_id
            offer_resource
            offer_amount
            price
            accepted
            date
          }
        }
      }
    }
    """
    try:
        response = requests.post(GRAPHQL_URL, json={"query": trade_query})
        trades = response.json()["data"]["nations"]["data"][0]["trades"]
    except Exception as e:
        return await interaction.followup.send(f"❌ Error fetching trades: {e}")

    if not trades:
        return await interaction.followup.send("❌ No trades found for Neprito.")

    # Sort trades descending by date
    trades = sorted(trades, key=lambda t: isoparse(t["date"]).replace(second=0, microsecond=0).astimezone(UTC), reverse=True)

    latest_trade = trades[0]
    trade_date = isoparse(latest_trade["date"]).replace(second=0, microsecond=0).astimezone(UTC)

    # Debug print exactly as you requested
    if trade_date == sheet_date:
        print("No")
        print(trade_date)
        print(date_sheet_str)
    else:
        print("Yes")
        print(trade_date)
        print(date_sheet_str)

    # Check if trade date matches sheet date
    if sheet_date is not None and trade_date == sheet_date:
        return await interaction.followup.send("❌ Trade already processed, not enough funds to deposit again.")

    # Validate the trade: accepted, sender_id in members, offer_amount=1, offer_resource="food"
    try:
        member_ids = json.loads(row.get("members", "[]"))
    except Exception:
        member_ids = []

    if not (latest_trade["accepted"] and int(latest_trade["sender_id"]) in member_ids and
            latest_trade["offer_amount"] == 1 and latest_trade["offer_resource"] == "food"):
        return await interaction.followup.send("❌ No valid matching trade found.")

    # Check amount requested vs trade price
    trade_paid = int(latest_trade["price"])
    if amount > trade_paid:
        return await interaction.followup.send(
            f"❌ You offered to deposit ${amount}, but the trade only paid ${trade_paid}."
        )

    # Deposit logic
    current_loans = int(row["loans"])
    current_balance = int(row["money"])
    to_loan = min(trade_paid, current_loans)
    to_balance = trade_paid - to_loan
    new_loans = current_loans - to_loan
    new_balance = current_balance + to_balance

    if new_balance > 1_000_000_000:
        return await interaction.followup.send("❌ Cannot exceed safekeep limit of $1,000,000,000.")

    # Save date back as ISO8601 string with Z timezone indicator
    new_date_str = trade_date.isoformat().replace("+00:00", "Z")

    try:
        sheet.update_cell(row_index, 4, new_loans)        # loans column index
        sheet.update_cell(row_index, 3, new_balance)      # money column index
        sheet.update_cell(row_index, 8, new_date_str)     # deposit_history column index
    except Exception as e:
        return await interaction.followup.send(f"❌ Failed to update sheet: {e}")

    # Confirmation message
    msg = f"💵 Deposit of ${trade_paid} processed from trade ID `{latest_trade['id']}`.\n"
    if to_loan > 0:
        msg += f"🧾 ${to_loan} went to repay loans (remaining debt: ${new_loans}).\n"
    if to_balance > 0:
        msg += f"💰 ${to_balance} added to balance (new balance: ${new_balance})."
    await interaction.followup.send(msg)




@bot.tree.command(name="trust", description="Set a user's trust level")
@app_commands.describe(member="User to set trust for", amount="Maximum advisory loan limit")
async def trust(interaction: discord.Interaction, member: discord.Member, amount: int):
    await interaction.response.defer(ephemeral=True)
    if not any(role.name == "Staff" for role in interaction.user.roles):
        return await interaction.followup.send("🚫 Only Staff can use this command.")
    sheet, row_index, row = get_user_row(member.id)
    if not row:
        return await interaction.followup.send("❌ User does not have an account.")
    sheet.update_cell(row_index, 6, amount)
    await interaction.followup.send(f"✅ Set trust level for <@{member.id}> to ${amount}")


@bot.tree.command(name="mmr_audit", description="Audits the MMR of the Member and gives suggestions")
@app_commands.describe(who="The Discord Member you wish to audit")
async def mmr_audit(interaction: discord.Interaction, who: discord.Member):
    try:
        await interaction.response.defer()
        user_id = str(interaction.user.id)
    
        global cached_users  # the dict version
        
        user_data = cached_users.get(user_id)   # user_id as int, no need to cast to string if keys are ints
        
        if not user_data:
            await interaction.followup.send("❌ You are not registered. Use `/register` first.")
            return
        
        own_id = str(user_data.get("NationID", "")).strip()

        if not own_id:
                await interaction.followup.send("❌ Could not find your Nation ID in the sheet.")
                return
        target_username = who.name.lower()

        target_discord_id = None
        for discord_id, info in cached_users.items():
            if info['DiscordUsername'].lower() == target_username:
                target_discord_id = discord_id
                break

        if target_discord_id is None:
            await interaction.followup.send(
                f"❌ Could not find Nation ID for {who.mention}. "
                "They must be registered in the Google Sheet with their Discord username."
            )
            return

        async def is_banker(interaction):
            return (
                any(role.name == "Government member" for role in interaction.user.roles)
                or str(interaction.user.id) == "1148678095176474678"
            )

        if not await is_banker(interaction):
            await interaction.followup.send("❌ You don't have the rights to perform this action.")
            return

        nation_id = int(cached_users[target_discord_id]["NationID"])
        GRAPHQL_URL = f"https://api.politicsandwar.com/graphql?api_key={API_KEY}"

        query = """
        query GetNationData($id: [Int]) {
        nations(id: $id) {
            data {
            num_cities
            cities {
                name
                barracks
                factory
                hangar
                drydock
            }
            }
        }
        }
        """

        variables = {"id": [nation_id]}

        response = requests.post(
            GRAPHQL_URL,
            json={"query": query, "variables": variables},
            headers={"Content-Type": "application/json"}
        )

        if response.status_code != 200:
            print(f"Request failed: {response.status_code}")
            # handle error here or return

        json_data = response.json()
        if "errors" in json_data:
            print("API returned errors:", json_data["errors"])
            # handle error here or return

        nation_list = json_data.get("data", {}).get("nations", {}).get("data", [])
        if not nation_list:
            print("No nation data found")
            # handle no data case here
            return

        nation_data = nation_list[0]

        nation_name = nation_data.get("nation_name", "Unknown Nation")
        num_cities = nation_data.get("num_cities", 0)
        cities = nation_data.get("cities", [])

        barracks = sum(city.get("barracks", 0) for city in cities)
        factory = sum(city.get("factory", 0) for city in cities)
        hangar = sum(city.get("hangar", 0) for city in cities)
        drydocks = sum(city.get("drydock", 0) for city in cities)

        military_data = get_military(nation_id)
        if military_data is None:
            await interaction.followup.send("❌ Could not retrieve military data for this nation.")
            return
        (
            nation_name,
            leader_name,
            score,
            warpolicy,
            soldiers,
            tanks,
            aircraft,
            ships,
            spies,
            missiles,
            nukes,
        ) = military_data

        valid_mmrs = (
            [[0, 5, 5, 1], [5, 5, 5, 3]] if num_cities < 16 else [[0, 3, 5, 1], [5, 5, 5, 3]]
        )

        from collections import Counter

        def distribute_structures(total, parts):
            if parts == 0:
                return []
            base = total // parts
            extras = total % parts
            return [base + (1 if i < extras else 0) for i in range(parts)]

        b_list = distribute_structures(barracks, num_cities)
        f_list = distribute_structures(factory, num_cities)
        h_list = distribute_structures(hangar, num_cities)
        d_list = distribute_structures(drydocks, num_cities)

        city_mmrs = list(zip(b_list, f_list, h_list, d_list))
        mmr_counts = Counter(city_mmrs)

        # Validate: all city MMRs must be in valid options
        is_valid = all([b, f, h, d] in valid_mmrs for (b, f, h, d) in city_mmrs)

        grouped_mmr_string = "\n".join(
            f"{count} Cities: {b}/{f}/{h}/{d}" for (b, f, h, d), count in sorted(mmr_counts.items(), reverse=True)
        )

        hrr = who.display_name
        if hrr in ["Barring(Economics Minister)", "MasterAced"]:
            whom = "~:heart: My Pookie :heart:~"
        elif hrr in ["IA Minister Speckgard", "Speckgard"]:
            whom = "Gooner"
        else:
            whom = who.display_name

        valid_options = "\n".join(f"{m[0]}/{m[1]}/{m[2]}/{m[3]}" for m in valid_mmrs)
        embed = discord.Embed(
            title=f"MMR Audit for {whom}",
            color=discord.Color.green() if is_valid else discord.Color.red(),
        )
        embed.add_field(name="Cities", value=str(num_cities), inline=False)
        embed.add_field(name="Grouped City MMRs", value=grouped_mmr_string, inline=False)
        embed.add_field(name="Soldiers", value=f"{soldiers}/{barracks*3000} (Missing {barracks*3000-soldiers} Soldiers)", inline=False)
        embed.add_field(name="Tanks", value=f"{tanks}/{factory*250} (Missing {factory*250-tanks} Tanks)", inline=False)
        embed.add_field(name="Aircrafts", value=f"{aircraft}/{hangar*15} (Missing {hangar*15-aircraft} Aircrafts)", inline=False)
        embed.add_field(name="Ships", value=f"{ships}/{drydocks*5} (Missing {drydocks*5-ships} Ships)", inline=False)
        embed.add_field(
            name="Status",
            value="✅ Valid MMR" if is_valid else "❌ Invalid MMR",
            inline=False,
        )
        if not is_valid:
            embed.add_field(name="Valid Options", value=valid_options, inline=False)
  # you need to define message_text below or adjust as needed

        # Prepare a plain text message for the view's description_text or send separately
        message_text = (
            f"**Cities:** {num_cities}\n"
            f"**Grouped City MMRs:**\n{grouped_mmr_string}\n"
            f"**Soldiers:** {soldiers}/{barracks*3000}\n"
            f"**Status:** {'✅ Valid MMR' if is_valid else '❌ Invalid MMR'}\n"
        )
        if not is_valid:
            message_text += f"**Valid Options:**\n{valid_options}\n"
        view = MMRView(
            is_valid=is_valid,
            soldiers=soldiers,
            barracks=barracks,
            factory=factory,
            tanks=tanks,
            aircraft=aircraft,
            ships=ships,
            drydocks=drydocks,
            hangars=hangar,
            num_cities=num_cities
        )
        image_url = "https://i.ibb.co/qJygzr7/Leonardo-Phoenix-A-dazzling-star-emits-white-to-bluish-light-s-2.jpg"
        embed.set_footer(text=f"Brought to you by Darkstar", icon_url=image_url)
        await interaction.followup.send(embed=embed, view=view)

    except Exception as e:
        await interaction.followup.send(f"❌ An unexpected error occurred: {e}")
        

    
    

@bot.tree.command(name="res_details_for_alliance", description="Get each Alliance Member's resources and money individually")
async def res_details_for_alliance(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True)

    sheet = get_registration_sheet()
    rows = sheet.get_all_records()
    user_id = str(interaction.user.id)
    
    # Find the user's data directly from the rows
    user_data = next(
        (r for r in rows if str(r.get("DiscordID", "")).strip() == user_id),
        None
    )
    
    if not user_data:
        await interaction.followup.send("❌ You are not registered. Use `/register` first.")
        return
    
    own_id = str(user_data.get("NationID", "")).strip()
    
    if not own_id:
        await interaction.followup.send("❌ Could not find your Nation ID in the sheet.")
        return
    
    async def is_banker(interaction):
        return (
            any(role.name == "Government member" for role in interaction.user.roles)
            or user_id == "1148678095176474678"
        )
    
    if not await is_banker(interaction):
        await interaction.followup.send("❌ You don't have the rights, lil bro.")
        return
    
    lines = []
    processed_nations = 0
    failed = 0
    
    totals = {
        "money": 0,
        "food": 0,
        "gasoline": 0,
        "munitions": 0,
        "steel": 0,
        "aluminum": 0,
        "bauxite": 0,
        "lead": 0,
        "iron": 0,
        "oil": 0,
        "coal": 0,
        "uranium": 0,
        "num_cities": 0,
    }
    batch_count = 0
    for row in rows:
        nation_id = str(row.get("NationID", "")).strip()
        row_user_id = str(row.get("DiscordID", "")).strip()

        try:
            result = get_resources(nation_id)
            if len(result) != 14:
                raise ValueError("Invalid result length from get_resources")

            (
                nation_name,
                num_cities,
                food,
                money,
                gasoline,
                munitions,
                steel,
                aluminum,
                bauxite,
                lead,
                iron,
                oil,
                coal,
                uranium
            ) = result

            totals["money"] += money
            totals["food"] += food
            totals["gasoline"] += gasoline
            totals["munitions"] += munitions
            totals["steel"] += steel
            totals["aluminum"] += aluminum
            totals["bauxite"] += bauxite
            totals["lead"] += lead
            totals["iron"] += iron
            totals["oil"] += oil
            totals["coal"] += coal
            totals["uranium"] += uranium
            totals["num_cities"] += num_cities
            processed_nations += 1

            lines.append(
                f"{nation_name} (ID: {own_id}): Cities={num_cities}, Money=${money:,}, "
                f"Food={food:,}, Gasoline={gasoline:,}, Munitions={munitions:,}, "
                f"Steel={steel:,}, Aluminum={aluminum:,}, Bauxite={bauxite:,}, "
                f"Lead={lead:,}, Iron={iron:,}, Oil={oil:,}, Coal={coal:,}, Uranium={uranium:,}"
            )
            batch_count += 1

            if batch_count == 30:
                await asyncio.sleep(32)
                batch_count = 0# to respect rate limits

        except Exception as e:
            print(f"Failed processing nation {own_id}: {e}")
            failed += 1
            continue

    total_resources_line = (
        f"\nAlliance totals - Nations counted: {processed_nations}, Failed: {failed}\n"
        f"Total Cities: {totals['num_cities']:,}\n"
        f"Money: ${totals['money']:,}\n"
        f"Food: {totals['food']:,}\n"
        f"Gasoline: {totals['gasoline']:,}\n"
        f"Munitions: {totals['munitions']:,}\n"
        f"Steel: {totals['steel']:,}\n"
        f"Aluminum: {totals['aluminum']:,}\n"
        f"Bauxite: {totals['bauxite']:,}\n"
        f"Lead: {totals['lead']:,}\n"
        f"Iron: {totals['iron']:,}\n"
        f"Oil: {totals['oil']:,}\n"
        f"Coal: {totals['coal']:,}\n"
        f"Uranium: {totals['uranium']:,}\n"
    )

    text_content = "\n".join(lines) + total_resources_line
    

    embed = discord.Embed(
        title="Alliance Members' Resources and Money (Detailed)",
        description=f"Nations counted: **{processed_nations}**\nFailed to retrieve data for: **{failed}**",
        colour=discord.Colour.dark_magenta()
    )

    image_url = "https://i.ibb.co/qJygzr7/Leonardo-Phoenix-A-dazzling-star-emits-white-to-bluish-light-s-2.jpg"
    embed.set_footer(text=f"Brought to you by Darkstar", icon_url=image_url)
    try:
        await interaction.followup.send(embed=embed,  file=discord.File(io.StringIO(text_content), filename="alliance_resources.txt"))
    except Exception as e:
        print(f"Error sending detailed resources file: {e}")
        await interaction.followup.send(embed=embed)

import asyncio
import io
import requests
import discord
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from matplotlib.ticker import FuncFormatter, MaxNLocator
import asyncio
import discord
from discord import app_commands
from datetime import datetime, timezone
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.ticker import FuncFormatter
import io
import pandas as pd  # We'll use pandas for daily aggregation
import requests
'''
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options

@bot.tree.command(name="check_site", description="Check for messages and buttons on a site.")
async def check_site(interaction: discord.Interaction):
    await interaction.response.defer()

    options = Options()
    options.add_argument("--headless")  # Optional: run in headless mode
    options.add_argument("user-agent=Mozilla/5.0")  # Helps avoid bot detection
    driver = webdriver.Chrome(options=options)

    results = []

    try:
        driver.get("https://politicsandwar.com/obl/host/")
        page_text = driver.page_source.lower()

        if "login" in page_text:
            results.append("Login requested")

        if "are you a robot?" in page_text:
            try:
                driver.switch_to.frame(driver.find_element(By.XPATH, "//iframe[contains(@src, 'recaptcha')]"))
                checkbox = driver.find_element(By.ID, "recaptcha-anchor")
                checkbox.click()
                driver.switch_to.default_content()
                results.append("Clicked 'I'm not a robot'")
            except:
                results.append("CAPTCHA interaction failed")

        try:
            host_div = driver.find_element(By.XPATH, "//div[@class='columnheader' and contains(text(), 'Host Home Game')]")
            host_div.click()
            results.append("Clicked 'Host Home Game'")
        except:
            results.append("'Host Home Game' not found")

        await interaction.followup.send("\n".join(results))

    except Exception as e:
        await interaction.followup.send(f"Error occurred: {e}")
    finally:
        driver.quit()
        '''

@bot.tree.command(name="auto_week_summary", description="See the total materials which are requested for this week")
async def auto_week_summary(interaction: discord.Interaction):
    await interaction.response.defer()
    try:
        sheet = get_auto_requests_sheet()
        all_rows = await asyncio.to_thread(sheet.get_all_values)

        if not all_rows or len(all_rows) < 2:
            await interaction.followup.send("No data available.", ephemeral=True)
            return

        header = all_rows[0]
        col_index = {col: idx for idx, col in enumerate(header)}
        rows = all_rows[1:]

        total_week = {res: 0 for res in ["Coal", "Oil", "Bauxite", "Lead", "Iron"]}

        for row in rows:
            if not any(row):  # skip empty rows
                continue
            try:
                time_period = float(row[col_index["TimePeriod"]]) if row[col_index["TimePeriod"]] else 1
                if time_period <= 0:
                    continue

                for res in total_week:
                    val_str = row[col_index[res]].strip()
                    amount = float(val_str) if val_str else 0
                    per_day = amount / time_period
                    total_week[res] += per_day * 5  # Weekly total
            except Exception as row_ex:
                print(f"Skipping row due to error: {row_ex}")
                continue

        formatted = [f"{emoji} **{res}**: {int(amount):,}".replace(",", ".") for res, emoji, amount in zip(
            ["Coal", "Oil", "Bauxite", "Lead", "Iron"],
            ["🪨", "🛢️", "🟤", "🪫", "⛓️"],
            total_week.values()
        )]

        embed = discord.Embed(
            title="📦 Auto-Requested Weekly Summary",
            description="\n".join(formatted),
            color=discord.Color.blue()
        )
        embed.set_footer(text="Calculated from current auto-request data")

        await interaction.followup.send(embed=embed)

    except Exception as e:
        print(f"Error in /auto_week_summary: {e}")
        await interaction.followup.send("❌ Error generating summary.", ephemeral=True)



@bot.tree.command(name="res_in_m_for_a", description="Get total Alliance Members' resources and money")
@app_commands.describe(
    mode="Group data by time unit",
    scale="Scale for Y-axis (Millions or Billions)"
)
@app_commands.choices(
    mode=[
        app_commands.Choice(name="Hourly", value="hours"),
        app_commands.Choice(name="Daily", value="days")
    ],
    scale=[
        app_commands.Choice(name="Millions", value="millions"),
        app_commands.Choice(name="Billions", value="billions")
    ]
)
async def res_in_m_for_a(
    interaction: discord.Interaction,
    mode: app_commands.Choice[str] = None,
    scale: app_commands.Choice[str] = None
):
    await interaction.response.defer()
    global money_snapshots
    user_id = str(interaction.user.id)
    
    global cached_users  # the dict version
    
    user_data = cached_users.get(user_id)   # user_id as int, no need to cast to string if keys are ints
    
    if not user_data:
        await interaction.followup.send("❌ You are not registered. Use `/register` first.")
        return
    
    own_id = str(user_data.get("NationID", "")).strip()

    if not own_id:
            await interaction.followup.send("❌ Could not find your Nation ID in the sheet.")
            return
    
    async def is_banker(interaction):
        return (
        any(role.name == "Government member" for role in interaction.user.roles)
            or str(interaction.user.id) == "1148678095176474678"
        )

    if not await is_banker(interaction):
        await interaction.followup.send("❌ You don't have the rights, lil bro.")
        return

    totals = {
        "money": 0,
        "food": 0,
        "gasoline": 0,
        "munitions": 0,
        "steel": 0,
        "aluminum": 0,
        "bauxite": 0,
        "lead": 0,
        "iron": 0,
        "oil": 0,
        "coal": 0,
        "uranium": 0,
        "num_cities": 0,
    }

    processed_nations = 0
    failed = 0

    GRAPHQL_URL = f"https://api.politicsandwar.com/graphql?api_key={API_KEY}"
    prices_query = """
    {
      top_trade_info {
        resources {
          resource
          average_price
        }
      }
    }
    """
    resource_prices = {}
    try:
        response = requests.post(
            GRAPHQL_URL,
            json={"query": prices_query},
            headers={"Content-Type": "application/json"}
        )
        data = response.json()
        for item in data["data"]["top_trade_info"]["resources"]:
            resource_prices[item["resource"]] = float(item["average_price"])
    except Exception as e:
        print(f"Error fetching resource prices: {e}")

    sheet = get_registration_sheet()
    rows = sheet.get_all_records()
    batch_count = 0

    for row in rows:
        nation_id = str(row.get("NationID", "")).strip()
        user_id = str(row.get("DiscordID", "")).strip()

        try:
            result = get_resources(nation_id)
            if len(result) != 14:
                raise ValueError("Invalid result length from get_resources")

            (
                nation_name,
                num_cities,
                food,
                money,
                gasoline,
                munitions,
                steel,
                aluminum,
                bauxite,
                lead,
                iron,
                oil,
                coal,
                uranium
            ) = result

            totals["money"] += money
            totals["food"] += food
            totals["gasoline"] += gasoline
            totals["munitions"] += munitions
            totals["steel"] += steel
            totals["aluminum"] += aluminum
            totals["bauxite"] += bauxite
            totals["lead"] += lead
            totals["iron"] += iron
            totals["oil"] += oil
            totals["coal"] += coal
            totals["uranium"] += uranium
            totals["num_cities"] += num_cities
            processed_nations += 1
            batch_count += 1
            if batch_count == 30:
                await asyncio.sleep(32)
                batch_count = 0

        except Exception as e:
            print(f"Failed processing nation {nation_id}: {e}")
            failed += 1
            continue

    total_sell_value = totals["money"]
    for resource in [
        "food", "gasoline", "munitions", "steel", "aluminum",
        "bauxite", "lead", "iron", "oil", "coal", "uranium"
    ]:
        amount = totals.get(resource, 0)
        price = resource_prices.get(resource, 0)
        total_sell_value += amount * price

    embed = discord.Embed(
        title="Alliance Total Resources & Money",
        colour=discord.Colour.dark_magenta()
    )
    embed.description = (
        f"🧮 Nations counted: **{processed_nations}**\n"
        f"⚠️ Failed to retrieve data for: **{failed}**\n\n"
        f"🌆 Total Cities: **{totals['num_cities']:,}**\n"
        f"💰 Money: **${totals['money']:,}**\n"
        f"🍞 Food: **{totals['food']:,}**\n"
        f"⛽ Gasoline: **{totals['gasoline']:,}**\n"
        f"💣 Munitions: **{totals['munitions']:,}**\n"
        f"🏗️ Steel: **{totals['steel']:,}**\n"
        f"🧱 Aluminum: **{totals['aluminum']:,}**\n"
        f"🪨 Bauxite: **{totals['bauxite']:,}**\n"
        f"🧪 Lead: **{totals['lead']:,}**\n"
        f"⚙️ Iron: **{totals['iron']:,}**\n"
        f"🛢️ Oil: **{totals['oil']:,}**\n"
        f"🏭 Coal: **{totals['coal']:,}**\n"
        f"☢️ Uranium: **{totals['uranium']:,}**\n\n"
        f"💸 Total Money if all was sold: **${total_sell_value:,.2f}**"
    )

    try:
        sheet = get_alliance_sheet()
        rows = sheet.get_all_records()

        df = pd.DataFrame(rows)
        df.columns = [col.strip() for col in df.columns]

        # Parse datetime
        df["TimeT"] = pd.to_datetime(df["TimeT"], errors='coerce', utc=True)
        df = df.dropna(subset=["TimeT"])

        resource_cols = [
            "Money", "Food", "Gasoline", "Munitions", "Steel", "Aluminum",
            "Bauxite", "Lead", "Iron", "Oil", "Coal", "Uranium"
        ]

        color_map = {
            "Money": "#1f77b4",
            "Food": "#ff7f0e",
            "Gasoline": "#2ca02c",
            "Munitions": "#d62728",
            "Steel": "#9467bd",
            "Aluminum": "#8c564b",
            "Bauxite": "#e377c2",
            "Lead": "#7f7f7f",
            "Iron": "#bcbd22",
            "Oil": "#17becf",
            "Coal": "#aec7e8",
            "Uranium": "#ffbb78"
        }
        resource_cols = [col for col in resource_cols if col in df.columns]

        # Clean and convert resources
        for col in resource_cols:
            df[col] = (
                df[col]
                .astype(str)
                .str.replace(",", ".", regex=False)
                .str.replace(" ", "", regex=False)
                .str.replace(u"\u00A0", "", regex=False)
                .str.extract(r"([\d.]+)", expand=False)
                .astype(float)
            )

        # Clean TotalMoney and set Total
        df["TotalMoney"] = (
            df["TotalMoney"]
            .astype(str)
            .str.replace(",", ".", regex=False)
            .str.replace(" ", "", regex=False)
            .str.replace(u"\u00A0", "", regex=False)
            .str.extract(r"([\d.]+)", expand=False)
            .astype(float)
        )
        df["Total"] = df["TotalMoney"]

        # Resample by time
        df = df.sort_values("TimeT").set_index("TimeT")

        if mode and mode.value.lower() == "days":
            df = df.resample("d").mean().interpolate()
            df = df[df.index >= (df.index.max() - pd.Timedelta(days=7))]
        else:
            df = df.resample("h").max().interpolate()
            df = df[df.index >= (df.index.max() - pd.Timedelta(hours=24))]
        
        df = df.reset_index()


    except Exception as e:
        print(f"Failed loading/parsing sheet data for graph: {e}")
        await interaction.followup.send(embed=embed)
        return

    # === Plotting ===
    try:
        value_scale = scale.value if scale else "millions"
        divisor = {"billions": 1e9, "millions": 1e6}.get(value_scale, 1)
        label_suffix = {"billions": "B", "millions": "M"}.get(value_scale, "")

        def format_yaxis(value, pos):
            return f"{value:,.2f}{label_suffix}"

        plt.style.use("ggplot")
        fig, ax = plt.subplots(figsize=(13, 8))

        times = df["TimeT"]

        for resource in resource_cols:
            ax.plot(times, df[resource] / divisor, label=resource, color=color_map[resource])

        if mode and mode.value.lower() == "days":
            ax.xaxis.set_major_formatter(mdates.DateFormatter("%d-%m"))
            ax.set_xlim(times.min(), times.max())
            ax.xaxis.set_major_locator(mdates.DayLocator())
        else:
            ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
            ax.set_xlim(times.min(), times.max())
            ax.xaxis.set_major_locator(mdates.HourLocator(interval=2))
            plt.setp(ax.get_xticklabels(), rotation=30, ha='right')

        ax.set_xlim(times.min(), times.max())
        ax.yaxis.set_major_formatter(FuncFormatter(format_yaxis))
        ax.set_ylabel(f"Resources ({label_suffix})")
        ax.set_title("Alliance Resources Over Time")
        ax.legend(loc="upper left", fontsize=8, frameon=False, ncols=len(resource_cols))
        plt.tight_layout()
        plt.grid(False)

        ax_total = ax.twinx()
        ax_total.plot(times, df["Total"] / divisor, label="Total", color="black", linewidth=3)
        ax_total.yaxis.set_major_formatter(FuncFormatter(format_yaxis))

        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=150)
        plt.close(fig)
        buf.seek(0)

        image_url = "https://i.ibb.co/qJygzr7/Leonardo-Phoenix-A-dazzling-star-emits-white-to-bluish-light-s-2.jpg"
        embed.set_footer(text=f"Brought to you by Darkstar", icon_url=image_url)
        await interaction.followup.send(embed=embed, file=discord.File(fp=buf, filename="resources_graph.png"))

    except Exception as e:
        print(f"Failed to generate or send graph: {e}")
        await interaction.followup.send(embed=embed)



            

@bot.tree.command(name="start_conflict", description="Start a new conflict.")
@app_commands.describe(
    conflict_name="Name of the new conflict",
    message_to_members="Message to the members",
    enemy_alliance_ids="Comma-separated list of enemy alliance IDs"
)
async def start_conflict(interaction: discord.Interaction, conflict_name: str, message_to_members: str = None, enemy_alliance_ids: str = None):
    await interaction.response.defer()
    load_conflict_data()

    if any(str(c.get("Name", "")).lower() == conflict_name.lower() for c in cached_conflicts):
        await interaction.followup.send(f"❌ Conflict '{conflict_name}' already exists.")
        return

    enemy_ids = [int(id.strip()) for id in enemy_alliance_ids.split(",") if id.strip().isdigit()] if enemy_alliance_ids else []
    declaring_alliance_id = 10259
    today = date.today().isoformat()

    GRAPHQL_URL = f"https://api.politicsandwar.com/graphql?api_key={API_KEY}"
    headers = {"Content-Type": "application/json"}

    query = """
    query($id: [Int], $limit: Int) {
        alliances(id: $id) {
            data {
                id
                name
                wars(limit: $limit, orderBy: [{ column: DATE, order: DESC }]) {
                    id
                    date
                    end_date
                    winner_id
                    attacker {
                        id
                        nation_name
                        alliance_id
                        wars {
                            id
                            attacks { money_stolen }
                        }
                    }
                    defender {
                        id
                        nation_name
                        alliance_id
                        wars {
                            id
                            attacks { money_stolen }
                        }
                    }
                }
            }
        }
    }
    """

    variables = {"id": [declaring_alliance_id], "limit": 50}

    try:
        response = requests.post(GRAPHQL_URL, json={"query": query, "variables": variables}, headers=headers)
        response.raise_for_status()
        result = response.json()
    except requests.RequestException as e:
        await interaction.followup.send(f"❌ Error fetching wars: {e}")
        return

    if "errors" in result:
        await interaction.followup.send(f"API error: {result['errors']}")
        return

    sheet = get_conflict_data_sheet()
    existing_war_ids = set(str(row[3]) for row in sheet.get_all_values()[1:] if row[3])

    alliances = result.get("data", {}).get("alliances", {}).get("data", [])
    if not alliances:
        await interaction.followup.send("❌ No alliance data found.")
        return

    new_wars = []
    for alliance in alliances:
        for war in alliance.get("wars", []):
            war_id = str(war.get("id"))
            war_date = war.get("date", "")[:10]
            war_end = war.get("end_date", "")
            if war_id in existing_war_ids:
                continue

            if not war_end:
                continue  # skip active wars

            if war_date != today:
                continue  # skip wars not started today

            attacker = war["attacker"]
            defender = war["defender"]
            result_str = (
                "Attacker" if war.get("winner_id") == attacker.get("id") else
                "Defender" if war.get("winner_id") == defender.get("id") else
                "Draw"
            )

            att_money = sum((a.get("money_stolen") or 0) for w in attacker.get("wars", []) for a in w.get("attacks", []))
            def_money = sum((a.get("money_stolen") or 0) for w in defender.get("wars", []) for a in w.get("attacks", []))

            money_gained = att_money
            money_lost = def_money

            new_wars.append([
                conflict_name, war_date, war_end[:10], war_id,
                attacker.get("nation_name", ""), defender.get("nation_name", ""),
                result_str, str(money_gained), str(money_lost)
            ])

    if new_wars:
        sheet.append_rows(new_wars)

    log_to_alliance_conflict(conflict_name, today, enemy_ids=",".join(map(str, enemy_ids)), message=message_to_members or "")

    await interaction.followup.send(f"✅ Conflict '{conflict_name}' started. Wars logged from today: {len(new_wars)}")


@bot.tree.command(name="add_to_conflict", description="Add enemy alliances to an existing conflict.")
@app_commands.describe(
    conflict_name="Name of the existing conflict",
    enemy_alliance_ids="Comma-separated list of additional enemy alliance IDs"
)
async def add_to_conflict(interaction: discord.Interaction, conflict_name: str, enemy_alliance_ids: str):
    await interaction.response.defer()

    # Correctly load conflicts, not conflict_data
    load_conflicts_data()  # This loads cached_conflicts

    row_idx = None
    conflict = None

    for i, c in enumerate(cached_conflicts):
        if c.get("Name", "").lower() == conflict_name.lower() and c.get("Closed", "").lower() != "true":
            conflict = c
            row_idx = i + 2  # +2 for 1-based index and header row
            break

    if not conflict:
        await interaction.followup.send(f"❌ Open conflict '{conflict_name}' not found.")
        return

    existing_ids = str(conflict.get("EnemyIDs", ""))
    existing_id_set = set(map(int, filter(str.isdigit, existing_ids.split(",")))) if existing_ids else set()
    new_ids = set(map(int, filter(str.isdigit, enemy_alliance_ids.split(","))))
    updated_ids = existing_id_set.union(new_ids)
    updated_ids_str = ",".join(map(str, sorted(updated_ids)))

    sheet = get_conflict_sheet()
    headers = sheet.row_values(1)
    try:
        enemy_col_idx = headers.index("EnemyIDs") + 1  # Convert to 1-based index
    except ValueError:
        await interaction.followup.send("❌ Could not find 'EnemyIDs' column.")
        return

    # Update the sheet cell with new enemy IDs
    try:
        update_conflict_row(row_idx, enemy_col_idx, updated_ids_str)
    except Exception as e:
        await interaction.followup.send(f"❌ Failed to update conflict row: {e}")
        return

    await interaction.followup.send(f"✅ Added enemy alliances {list(new_ids)} to conflict '{conflict_name}'.")



@bot.tree.command(name="end_conflict", description="Mark an existing conflict as ended.")
@app_commands.describe(
    conflict_name="Name of the conflict to end"
)
async def end_conflict(interaction: discord.Interaction, conflict_name: str):
    await interaction.response.defer()
    from datetime import datetime, timezone
    end_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    try:
        sheet = get_conflict_sheet()
        records = sheet.get_all_values()
        found = False
        for i, row in enumerate(records[1:], start=2):
            if row[0].strip().lower() == conflict_name.lower():
                sheet.update_cell(i, 3, end_date)  # End Date
                sheet.update_cell(i, 4, "True")    # Closed
                found = True
                break

        if not found:
            await interaction.followup.send(f"❌ Conflict '{conflict_name}' not found.")
            return

        try:
            log_to_alliance_conflict(conflict_name, None, end_date)
        except Exception as log_err:
            print(f"⚠️ Logging error in Alliance Conflict sheet: {log_err}")

        await interaction.followup.send(f"✅ Conflict '{conflict_name}' marked as ended on {end_date}.")
    except Exception as e:
        print(f"❌ Failed to end conflict '{conflict_name}': {e}")
        await interaction.followup.send(f"❌ Failed to end conflict '{conflict_name}'. Check logs for details.")

@bot.tree.command(name="member_activity", description="Shows the activity of our members")
async def member_activity(interaction: discord.Interaction):
    await interaction.response.defer()
    user_id = str(interaction.user.id)

    global cached_users

    user_data = cached_users.get(user_id)

    if not user_data:
        await interaction.followup.send("❌ You are not registered. Use `/register` first.")
        return

    own_id = str(user_data.get("NationID", "")).strip()

    if not own_id:
        await interaction.followup.send("❌ Could not find your Nation ID in the sheet.")
        return

    async def is_banker(interaction):
        return (
            any(role.name == "Government member" for role in interaction.user.roles)
            or str(interaction.user.id) == "1148678095176474678"
        )

    if not await is_banker(interaction):
        await interaction.followup.send("❌ You don't have the rights, lil bro.")
        return

    activish = 0
    activish_wo_bloc = 0
    active_w_bloc = 0
    active_wo_bloc = 0
    inactive = 0
    activish_list = []
    activish_wo_bloc_list = []
    active_w_bloc_list = []
    active_wo_bloc_list = []
    inactive_list = []

    try:
        sheet = get_registration_sheet()
        rows = sheet.get_all_records()
        df = pd.DataFrame(rows)
        df.columns = [col.strip() for col in df.columns]
        nation_ids = df["NationID"].dropna().astype(int).tolist()
    except Exception as e:
        await interaction.followup.send(f"❌ Error loading Nation IDs: {e}")
        return

    for own_id in nation_ids:
        try:
            military_data = get_military(own_id)
            nation_name = military_data[0]
            nation_leader = military_data[1]
            score = military_data[2]
            result = get_general_data(own_id)
            if result is None or len(result) < 7:
                print(f"Missing data for nation {own_id}")
                continue

            alliance_id, alliance_position, alliance, domestic_policy, num_cities, colour, activity, *_ = result

            try:
                activity_dt = datetime.fromisoformat(activity)
            except (ValueError, TypeError):
                print(f"Invalid activity date for nation {own_id}: {activity}")
                continue

            now = datetime.now(timezone.utc)
            delta = now - activity_dt
            days_inactive = delta.total_seconds() / 86400

            if days_inactive >= 2:
                inactive += 1
                inactive_list.append(f"Nation: {nation_name}(ID: `{own_id}`), Leader: {nation_leader}, Bloc: {colour}, Score: {score}\n")
            elif days_inactive >= 1:
                if colour.lower() == "black":
                    activish += 1
                    activish_list.append(f"Nation: {nation_name}(ID: `{own_id}`), Leader: {nation_leader}, Bloc: {colour}, Score: {score}\n")
                else:
                    activish_wo_bloc += 1
                    activish_wo_bloc_list.append(f"Nation: {nation_name}(ID: `{own_id}`), Leader: {nation_leader}, Bloc: {colour}, Score: {score}\n")
            else:
                if colour.lower() == "black":
                    active_w_bloc += 1
                    active_w_bloc_list.append(f"Nation: {nation_name}(ID: `{own_id}`), Leader: {nation_leader}, Bloc: {colour}, Score: {score}\n")
                else:
                    active_wo_bloc += 1
                    active_wo_bloc_list.append(f"Nation: {nation_name}(ID: `{own_id}`), Leader: {nation_leader}, Bloc: {colour}, Score: {score}\n")
            await asyncio.sleep(3)
        except Exception as e:
            print(f"Error processing nation ID {own_id}: {e}")
            continue

    data = [active_w_bloc, active_wo_bloc, activish, activish_wo_bloc, inactive]

    if sum(data) == 0:
        await interaction.followup.send("⚠️ No activity data available to generate chart.")
        return

    # Create pie chart
    fig, ax = plt.subplots(figsize=(8, 4), subplot_kw=dict(aspect="equal"))

    labels = [
        "Active (Correct Bloc)",
        "Active (Wrong Bloc)",
        "Activish (Correct Bloc, 1-2 Days)",
        "Activish (Wrong Bloc, 1-2 Days)",
        "Inactive (2+ Days)"
    ]

    def func(pct, allvals):
        absolute = int(np.round(pct / 100. * np.sum(allvals)))
        return f"{pct:.1f}%\n({absolute})"

    wedges, texts, autotexts = ax.pie(data, autopct=lambda pct: func(pct, data), textprops=dict(color="w"))

    ax.legend(wedges, labels,
              title="DS Member Statuses",
              loc="center left",
              bbox_to_anchor=(1, 0, 0.5, 1))

    plt.setp(autotexts, size=8, weight="bold")
    ax.set_title("DS Activity Chart")

    buffer = BytesIO()
    plt.savefig(buffer, format="png")
    buffer.seek(0)
    file = discord.File(fp=buffer, filename="ds_activity.png")

    embed = discord.Embed(
        title="📊 DS Activity",
        description="Here are the members not in ideal status categories:",
        color=discord.Color.dark_teal()
    )

    def add_field_chunks(embed, title, lines):
        if not lines:
            return
        current = ""
        for i, line in enumerate(lines):
            if len(current) + len(line) > 1024:
                embed.add_field(name=title if i == 0 else f"{title} (cont.)", value=current, inline=False)
                current = line
            else:
                current += line
        if current:
            embed.add_field(name=title if not embed.fields or embed.fields[-1].name != title else f"{title} (cont.)", value=current, inline=False)

    add_field_chunks(embed, "Active (Wrong Bloc)", active_wo_bloc_list)
    add_field_chunks(embed, "Activish (Correct Bloc)", activish_list)
    add_field_chunks(embed, "Activish (Wrong Bloc)", activish_wo_bloc_list)
    add_field_chunks(embed, "Inactive", inactive_list)

    image_url = "https://i.ibb.co/qJygzr7/Leonardo-Phoenix-A-dazzling-star-emits-white-to-bluish-light-s-2.jpg"
    embed.set_footer(text=f"Brought to you by Darkstar", icon_url=image_url)
    embed.set_image(url="attachment://ds_activity.png")

    await interaction.followup.send(embed=embed, file=file)



import discord
import requests
from io import BytesIO
import matplotlib.pyplot as plt
from collections import defaultdict
from datetime import datetime
from matplotlib.dates import DateFormatter
import matplotlib.dates as mdates

@bot.tree.command(name="war_losses", description="Show recent wars for a nation with optional detailed stats.")
@app_commands.describe(
    nation_id="Nation ID",
    detail="Optional detail to show: infra, money, soldiers",
    wars_count="Number of wars to fetch (default 30)"
)
@app_commands.choices(detail=[
    app_commands.Choice(name="infra", value="infra"),
    app_commands.Choice(name="soldiers", value="soldiers"),
])
async def war_losses(interaction: discord.Interaction, nation_id: int, detail: str = None, wars_count: int = 30):
    await interaction.response.defer()

    import requests
    from collections import defaultdict
    from datetime import datetime
    import matplotlib.pyplot as plt
    from io import BytesIO
    import discord
    user_id = str(interaction.user.id)
    
    global cached_users  # the dict version
    
    user_data = cached_users.get(user_id)   # user_id as int, no need to cast to string if keys are ints
    
    if not user_data:
        await interaction.followup.send("❌ You are not registered. Use `/register` first.")
        return
    
    own_id = str(user_data.get("NationID", "")).strip()

    if not own_id:
            await interaction.followup.send("❌ Could not find your Nation ID in the sheet.")
            return
    
    GRAPHQL_URL = f"https://api.politicsandwar.com/graphql?api_key={API_KEY}"

    query = """
    query (
      $nation_id: [Int], 
      $first: Int, 
      $page: Int, 
      $orderBy: [QueryWarsOrderByOrderByClause!], 
      $active: Boolean
    ) {
      wars(
        nation_id: $nation_id, 
        first: $first, 
        page: $page, 
        orderBy: $orderBy,
        active: $active
      ) {
        data {
          id
          date
          end_date
          reason
          war_type
          winner_id
          attacker {
            id
            nation_name
          }
          defender {
            id
            nation_name
          }
          att_infra_destroyed
          def_infra_destroyed
          att_money_looted
          def_money_looted
          def_soldiers_lost
          att_soldiers_lost
        }
      }
    }
    """

    variables = {
        "nation_id": [nation_id],
        "first": wars_count,
        "page": 1,
        "orderBy": [{"column": "ID", "order": "DESC"}],
        "active": False,
    }

    headers = {"Content-Type": "application/json"}

    try:
        response = requests.post(GRAPHQL_URL, json={"query": query, "variables": variables}, headers=headers)
        response.raise_for_status()
    except requests.RequestException as e:
        await interaction.followup.send(f"Error fetching data: {e}")
        return

    result = response.json()
    if "errors" in result:
        await interaction.followup.send(f"API errors: {result['errors']}")
        return

    wars = result.get("data", {}).get("wars", {}).get("data", [])
    if not wars:
        await interaction.followup.send("No wars found for this nation.")
        return

    all_log = ""
    war_results = []
    money_per_war = []

    for war in wars:
        war_id = war.get("id")
        winner_id = str(war.get("winner_id", "0"))

        attacker = war.get("attacker") or {}
        defender = war.get("defender") or {}

        atk_id = str(attacker.get("id", "0"))
        def_id = str(defender.get("id", "0"))
        atk_name = attacker.get("nation_name", "Unknown")
        def_name = defender.get("nation_name", "Unknown")
        nation_id_str = str(nation_id)

        # Determine war outcome
        if winner_id == nation_id_str:
            outcome_val = 1
            outcome = "Win"
        elif winner_id in [atk_id, def_id] and winner_id != nation_id_str:
            outcome_val = -1
            outcome = "Loss"
        else:
            outcome_val = 0
            outcome = "Draw"

        war_results.append(outcome_val)
        money = war.get("att_money_looted", 0) + war.get("def_money_looted", 0)
        money_per_war.append(money)

        line = f"War ID: {war_id} | Attacker: {atk_name} | Defender: {def_name} | Outcome: {outcome}"
        if detail == "infra":
            line += f" | Infra Destroyed - Att: {war.get('att_infra_destroyed', 0)}, Def: {war.get('def_infra_destroyed', 0)}"
        elif detail == "money":
            line += f" | Money Looted - Att: {war.get('att_money_looted', 0)}, Def: {war.get('def_money_looted', 0)}"
        elif detail == "soldiers":
            line += f" | Soldiers Lost - Att: {war.get('att_soldiers_lost', 0)}, Def: {war.get('def_soldiers_lost', 0)}"

        all_log += line + "\n"

    # Create combined outcome + money graph
    indices = list(range(1, len(war_results) + 1))
    looted_millions = [m / 1_000_000 for m in money_per_war]

    fig, ax1 = plt.subplots(figsize=(10, 5))
    ax1.bar(indices, looted_millions, width=0.6, color="red", label="Money Looted (M)", zorder=2)
    ax1.set_ylabel("Money ($M)")
    ax1.set_xlabel("War Index")
    ax1.set_xticks(indices)

    ax2 = ax1.twinx()
    ax2.plot(indices, war_results, color="blue", marker="o", label="Outcome", zorder=3)
    ax2.set_ylabel("Outcome")
    ax2.set_yticks([-1, 0, 1])
    ax2.set_yticklabels(["Loss", "Draw", "Win"])

    # Add horizontal lines for outcome clarity
    ax2.axhline(y=1, color="green", linestyle="--", linewidth=1, label="Win")
    ax2.axhline(y=0, color="gray", linestyle="--", linewidth=1, label="Draw")
    ax2.axhline(y=-1, color="red", linestyle="--", linewidth=1, label="Loss")

    ax1.set_xlim(0.5, len(indices) + 0.5)
    ax1.legend(loc="upper left")
    ax2.legend(loc="upper right")
    plt.title(f"Nation {nation_id} War Outcomes & Money Looted")
    plt.tight_layout()

    buf = BytesIO()
    plt.savefig(buf, format="png")
    plt.close()
    buf.seek(0)
    txt_buffer = BytesIO(all_log.encode("utf-8"))
    txt_buffer.seek(0)

    await interaction.followup.send(
        file=discord.File(buf, filename="combined_war_graph.png"),
        content=f"Combined War Outcome & Money Graph for Nation {nation_id}"
    )
    file=discord.File(txt_buffer, filename=f"nation_{nation_id}_wars_summary.txt")
    embed = discord.Embed(
        title="War Results:",
        colour=discord.Colour.dark_orange(),
        description=(file)
    )
    image_url = "https://i.ibb.co/qJygzr7/Leonardo-Phoenix-A-dazzling-star-emits-white-to-bluish-light-s-2.jpg"
    embed.set_footer(text=f"Brought to you by Darkstar", icon_url=image_url)
    # Send text summary
    await interaction.followup.send(embed=embed, file=discord.File(txt_buffer, filename=f"nation_{nation_id}_wars_summary.txt"))


# Here's the updated and complete code as requested:
# ✅ Integrated conflict-based graph plotting with proper headers and plotting logic
# ✅ Conflict name handling, graph title with last update, and graph generation for saved sheet data

from datetime import datetime, date
from collections import defaultdict
import matplotlib.pyplot as plt
from matplotlib.dates import DateFormatter
import matplotlib.dates as mdates
from io import BytesIO
import discord
import requests
from discord import app_commands
from dateutil import parser
import matplotlib.dates as mdates

@bot.tree.command(name="war_losses_alliance", description="Show recent wars for an alliance with optional detailed stats and conflict mode.")
@app_commands.describe(
    alliance_id="Alliance ID",
    war_count="Number of recent wars to display (default 30)",
    money_more_detail="Set to true to show detailed money and outcome graphs (default false)",
    conflict_name="Optional conflict name to get saved war stats and summary graph"
)
async def war_losses_alliance(interaction: discord.Interaction, alliance_id: int, war_count: int = 30, money_more_detail: bool = False, conflict_name: str = None):
    await interaction.response.defer()
    
    user_id = str(interaction.user.id)
    global cached_users
    user_data = cached_users.get(user_id)
    
    if not user_data:
        await interaction.followup.send("❌ You are not registered. Use `/register` first.")
        return
    
    own_id = str(user_data.get("NationID", "")).strip()
    if not own_id:
        await interaction.followup.send("❌ Could not find your Nation ID in the sheet.")
        return

    if conflict_name:
        # ✅ If conflict specified, show graph for saved conflict data
        try:
            sheet = get_conflict_data_sheet()
            all_rows = sheet.get_all_records()
        except Exception as e:
            await interaction.followup.send("❌ Failed to load conflict data.")
            return

        # Filter relevant rows
        # Filter relevant rows
        relevant_rows = [
        row for row in all_rows
        if str(row.get("Conflict Name", "")).lower() == conflict_name.lower()
    ]
    
        relevant_rows = relevant_rows[:war_count]  # Limit to requested count
        if not relevant_rows:
            await interaction.followup.send(f"❌ No saved wars found for conflict '{conflict_name}'.")
            return

        war_dates = []
        money_looted = []
        outcomes = []

        for row in relevant_rows:
            try:
                war_date = row.get("War Start Date") or row.get("War Date") or ""
                dt = datetime.strptime(war_date[:10], "%Y-%m-%d").date()
                war_dates.append(dt)

                # Looted money
                att_loot = float(row.get("Total Money Stolen (Attacker)", 0) or 0)
                def_loot = float(row.get("Total Money Stolen (Defender)", 0) or 0)
                money_looted.append(att_loot + def_loot)

                # Outcome logic
                outcome = row.get("Outcome", "").lower()
                if outcome == "attacker win":
                    outcomes.append(1)
                elif outcome == "defender win":
                    outcomes.append(-1)
                else:
                    outcomes.append(0)
            except Exception as e:
                print(f"⛔ Skipping bad conflict row: {e}")

        if not war_dates:
            await interaction.followup.send("❌ No valid data to graph.")
            return

        fig, ax1 = plt.subplots(figsize=(10, 5))

        ax1.bar(war_dates, money_looted, width=0.8, color="red", label="Money Looted")
        ax1.set_ylabel("Total Money Looted ($)")
        ax1.xaxis.set_major_formatter(DateFormatter("%Y-%m-%d"))
        ax1.xaxis.set_major_locator(mdates.DayLocator(interval=max(1, len(war_dates) // 10)))

        ax2 = ax1.twinx()
        ax2.plot(war_dates, outcomes, color="blue", marker="o", label="Outcome")
        ax2.set_ylabel("Outcome")
        ax2.set_yticks([-1, 0, 1])
        ax2.set_yticklabels(["Defender Win", "Draw", "Attacker Win"])

        plt.title(f"{conflict_name} - War Losses & Loot (Last update {datetime.now().strftime('%Y-%m-%d')})")
        plt.xticks(rotation=45)
        plt.tight_layout()

        buf = BytesIO()
        plt.savefig(buf, format="png")
        buf.seek(0)
        plt.close(fig)

        await interaction.followup.send(file=discord.File(buf, filename=f"{conflict_name}_summary.png"))
        return

    # ✅ CONTINUES WITH DEFAULT ALLIANCE WAR FETCHING IF NO CONFLICT NAME PROVIDED

    GRAPHQL_URL = f"https://api.politicsandwar.com/graphql?api_key={API_KEY}"
    orderBy = [{"column": "ID", "order": "DESC"}]

    query = """ query ( $id: [Int], $limit: Int, $orderBy: [AllianceWarsOrderByOrderByClause!] ) {
        alliances(id: $id) {
            data {
                id
                name
                wars(limit: $limit, orderBy: $orderBy) {
                    id
                    date
                    end_date
                    reason
                    war_type
                    winner_id
                    attacker { nation_name id alliance_id }
                    defender { nation_name id alliance_id }
                    att_infra_destroyed
                    def_infra_destroyed
                    def_soldiers_lost
                    att_soldiers_lost
                    att_money_looted
                    def_money_looted
                    attacks { money_stolen }
                }
            }
        }
    }"""

    variables = {"id": [alliance_id], "limit": 500, "orderBy": orderBy}
    headers = {"Content-Type": "application/json"}

    try:
        response = requests.post(GRAPHQL_URL, json={"query": query, "variables": variables}, headers=headers)
        response.raise_for_status()
    except requests.RequestException as e:
        await interaction.followup.send(f"Error fetching data: {e}")
        return

    result = response.json()
    if "errors" in result:
        await interaction.followup.send(f"API errors: {result['errors']}")
        return

    alliances_data = result.get("data", {}).get("alliances", {}).get("data", [])
    if not alliances_data:
        await interaction.followup.send("No alliance data found.")
        return
    alliance = alliances_data[0]
    wars = alliance.get("wars", [])[:war_count]  # ✅ Apply war_count limit

    # ⚙️ Save matching conflict data to sheet
    if cached_conflicts:
        try:
            sheet = get_conflict_data_sheet()
            all_saved_conflict_rows = sheet.get_all_records() or []
        except Exception as e:
            all_saved_conflict_rows = []
            print(f"⚠️ Failed to load existing conflict rows: {e}")

        existing_ids_set = set(str(row.get("War ID")) for row in all_saved_conflict_rows if row.get("War ID"))

        for conflict in cached_conflicts:
            try:
                start = datetime.strptime(conflict.get("Start"), "%Y-%m-%d").date()
                end_str = conflict.get("End")
                end = datetime.strptime(end_str, "%Y-%m-%d").date() if end_str else date.today()
            except Exception as e:
                continue

            for war in wars:
                war_id = str(war.get("id"))
                if war_id in existing_ids_set:
                    continue

                war_date_str = war.get("date", "")[:10]
                try:
                    war_date = datetime.strptime(war_date_str, "%Y-%m-%d").date()
                except Exception:
                    continue

                if start <= war_date <= end:
                    try:
                        attacker = war.get("attacker", {})
                        defender = war.get("defender", {})
                        winner_id = str(war.get("winner_id", ""))
                        attacker_id = str(attacker.get("id", ""))
                        defender_id = str(defender.get("id", ""))

                        if winner_id == attacker_id:
                            outcome = "Attacker Win"
                        elif winner_id == defender_id:
                            outcome = "Defender Win"
                        else:
                            outcome = "Draw"

                        att_loot = war.get("att_money_looted", 0) or 0
                        def_loot = war.get("def_money_looted", 0) or 0

                        sheet.append_row([
                            conflict.get("Name", "Unknown"),
                            attacker.get("nation_name", "Unknown"),
                            defender.get("nation_name", "Unknown"),
                            war_id,
                            war.get("war_type", ""),
                            war.get("reason", ""),
                            war.get("date", ""),
                            war.get("end_date", ""),
                            attacker.get("alliance_id", ""),
                            defender.get("alliance_id", ""),
                            war.get("att_infra_destroyed", 0),
                            war.get("def_infra_destroyed", 0),
                            war.get("att_soldiers_lost", 0),
                            war.get("def_soldiers_lost", 0),
                            att_loot,
                            def_loot,
                            outcome
                        ])
                        existing_ids_set.add(war_id)
                        break
                    except Exception as e:
                        print(f"❌ Failed to save conflict war: {e}")

    # ✅ Now back to your existing plotting logic for live wars
    # ✅ OMITTED FOR SPACE — reuse your existing plotting code below from your message




    def chunks(lst, n):
        for i in range(0, len(lst), n):
            yield lst[i:i + n]

    all_log = ""
    money_by_day = defaultdict(float)
    outcome_by_day = defaultdict(list)

    # Calculate money_looted as attacker loot + defender loot (total looted)
    # If needed change later, now using attacker loot as money_looted

    # Prepare outcomes and money per day
    # Inside your war processing loop:
    for idx, war in enumerate(wars):
        attacker = war.get("attacker") or {}
        defender = war.get("defender") or {}
        atk_alliance = str(attacker.get("alliance_id", 0))
        def_alliance = str(defender.get("alliance_id", 0))

        is_attacker = atk_alliance == str(alliance_id)
        is_defender = def_alliance == str(alliance_id)

        money_looted = war.get("att_money_looted", 0) if is_attacker else war.get("def_money_looted", 0)

        winner_id = str(war.get("winner_id"))
        atk_id = str(attacker.get("id", 0))
        def_id = str(defender.get("id", 0))

        if winner_id == atk_id and is_attacker:
            outcome = "Win"
            y_val = 1
        elif winner_id == def_id and is_defender:
            outcome = "Win"
            y_val = 1
        elif winner_id == def_id and is_attacker:
            outcome = "Loss"
            y_val = -1
        elif winner_id == atk_id and is_defender:
            outcome = "Loss"
            y_val = -1
        else:
            outcome = "Draw"
            y_val = 0

        war_datetime_raw = war.get("date")
        try:
            from dateutil import parser
            war_dt = parser.isoparse(war_datetime_raw)
            war_date = war_dt.date().isoformat()  # 'YYYY-MM-DD'
        except Exception as e:
            print(f"⛔ Failed to parse war date: {war_datetime_raw} | Error: {e}")
            continue

        # ✅ Store values here
        money_by_day[war_date] += money_looted
        outcome_by_day[war_date].append(y_val)

        all_log += (
            f"Date: {war_date} | {attacker.get('nation_name','?')} vs {defender.get('nation_name','?')} | "
            f"Outcome: {outcome} | Looted: {money_looted:,}\n"
        )

    # ✅ Move graph prep after the loop
# After all wars processed
    if money_more_detail:
    
        # Use all unique war dates from the wars list to ensure correct x-axis
        war_dates_all = sorted(set(
            datetime.strptime(war.get("date")[:10], "%Y-%m-%d").date()
            for war in wars if war.get("date")
        ))
    
        # Ensure mapping date strings to match keys in dictionaries
        values = [money_by_day[d.strftime("%Y-%m-%d")] for d in war_dates_all]
        outcome_avgs = [
            sum(outcome_by_day[d.strftime("%Y-%m-%d")]) / len(outcome_by_day[d.strftime("%Y-%m-%d")])
            for d in war_dates_all
        ]
    
        # ✅ Money Looted Bar Graph
        fig_money, ax_money = plt.subplots(figsize=(10, 5))
        ax_money.bar(war_dates_all, values, color="red")
        ax_money.set_title(f"{alliance['name']} - Money Looted Per Day")
        ax_money.set_ylabel("Money Looted ($M)")
        ax_money.xaxis.set_major_formatter(DateFormatter("%Y-%m-%d"))
        ax_money.xaxis.set_major_locator(mdates.DayLocator(interval=max(1, len(war_dates_all) // 10)))
        plt.xticks(rotation=45)
        plt.tight_layout()
    
        buf_money = BytesIO()
        plt.savefig(buf_money, format="png")
        buf_money.seek(0)
        plt.close(fig_money)
        await interaction.followup.send(file=discord.File(buf_money, filename="money_detail_graph.png"))
    
        # ✅ Outcome Average Line Graph
        fig_outcome, ax_outcome = plt.subplots(figsize=(10, 5))
        ax_outcome.plot(war_dates_all, outcome_avgs, color="blue", marker="o")
        ax_outcome.set_title(f"{alliance['name']} - Average Outcome Per Day")
        ax_outcome.set_ylabel("Outcome")
        ax_outcome.set_yticks([-1, 0, 1])
        ax_outcome.set_yticklabels(["Loss", "Draw", "Win"])
        ax_outcome.xaxis.set_major_formatter(DateFormatter("%Y-%m-%d"))
        ax_outcome.xaxis.set_major_locator(mdates.DayLocator(interval=max(1, len(war_dates_all) // 10)))
        plt.xticks(rotation=45)
        plt.tight_layout()
    
        buf_outcome = BytesIO()
        plt.savefig(buf_outcome, format="png")
        buf_outcome.seek(0)
        plt.close(fig_outcome)
        file=discord.File(buf_outcome, filename="outcome_detail_graph.png")
        embed = discord.Embed(
            title="##War Results:##",
            colour=discord.Colour.dark_orange(),
            description="Visialized War Results:"
        )
        image_url = "https://i.ibb.co/qJygzr7/Leonardo-Phoenix-A-dazzling-star-emits-white-to-bluish-light-s-2.jpg"
        embed.set_footer(text=f"Brought to you by Darkstar", icon_url=image_url)
        await interaction.followup.send(embed=embed)


    else:
        WARS_PER_GRAPH = 30
        # money_more_detail == False: generate combined graphs in chunks of WARS_PER_GRAPH
        for batch_index, war_batch in enumerate(chunks(wars, WARS_PER_GRAPH), start=1):
            war_results = []
            money_per_war = []

            for war in war_batch:
                attacker = war.get("attacker") or {}
                defender = war.get("defender") or {}
                atk_alliance = str(attacker.get("alliance_id", 0))
                def_alliance = str(defender.get("alliance_id", 0))

                is_attacker = atk_alliance == str(alliance_id)
                is_defender = def_alliance == str(alliance_id)

                money_looted = war.get("att_money_looted", 0) if is_attacker else war.get("def_money_looted", 0)

                winner_id = str(war.get("winner_id"))
                atk_id = str(attacker.get("id", 0))
                def_id = str(defender.get("id", 0))

                if winner_id == atk_id and is_attacker:
                    y_val = 1
                elif winner_id == def_id and is_defender:
                    y_val = 1
                elif winner_id == def_id and is_attacker:
                    y_val = -1
                elif winner_id == atk_id and is_defender:
                    y_val = -1
                else:
                    y_val = 0

                war_results.append(y_val)
                money_per_war.append(money_looted / 1_000_000)  # millions

            indices = list(range(1, len(war_results) + 1))

            fig, ax1 = plt.subplots(figsize=(9, 5))
            bar_width = 0.6

            # Money looted bars (red), centered
            ax1.bar(indices, money_per_war, width=bar_width, color="red", label="Money Looted (M)", align='center', zorder=2)
            ax1.set_ylabel("Money Looted ($M)")
            ax1.set_xlabel("War Number")
            ax1.set_xticks(indices)

            # Outcome line plot (blue)
            ax2 = ax1.twinx()
            ax2.plot(indices, war_results, color="blue", linestyle="-", marker="o", label="Outcome", zorder=1)
            ax2.set_ylabel("Outcome")
            ax2.set_yticks([-1, 0, 1])
            ax2.set_yticklabels(["Loss", "Draw", "Win"])
            ax2.grid(False)

            ax1.set_xlim(0.5, len(indices) + 0.5)

            # Legends outside the plot area
            ax1.legend(loc="upper center", bbox_to_anchor=(0.5, -0.15), ncol=1)
            ax2.legend(loc="upper center", bbox_to_anchor=(0.5, -0.25), ncol=1)

            plt.title(f"{alliance['name']} - War Batch {batch_index}")
            plt.tight_layout()

            buf = BytesIO()
            plt.savefig(buf, format="png")
            buf.seek(0)
            plt.close(fig)
            file=discord.File(buf, filename=f"war_graph_batch{batch_index}.png")
            embed = discord.Embed(
                title="War Results Alliance:",
                colour=discord.Colour.dark_orange(),
                description="Visualised Results:"
            )
            image_url = "https://i.ibb.co/qJygzr7/Leonardo-Phoenix-A-dazzling-star-emits-white-to-bluish-light-s-2.jpg"
            embed.set_footer(text=f"Brought to you by Darkstar", icon_url=image_url)
            embed.set_image(url=f"attachment://war_graph_batch{batch_index}.png")
            await interaction.followup.send(embed=embed, file=file)

    # Always send full war summary txt file at end
    log_file = BytesIO(all_log.encode("utf-8"))
    log_file.seek(0)
    await interaction.followup.send(file=discord.File(log_file, filename=f"war_summary_{alliance_id}.txt"))





'''@bot.tree.command(name="register_manual", description="Manually register a nation with a given Discord username (no validation)")
@app_commands.describe(
    nation_id="Nation ID number (e.g., 365325)",
    discord_username="Exact Discord username to register"
)
async def register_manual(interaction: discord.Interaction, nation_id: str, discord_username: str):
    await interaction.response.defer()

    if not str(interaction.user.id) == "1148678095176474678":
        await interaction.followup.send("Not a public command")
        return

    if not nation_id.isdigit():
        await interaction.followup.send("❌ Please enter only the Nation ID number, not a link.")
        return

    try:
        with open("Alliance.json", "r") as f:
            data = json.load(f)
    except FileNotFoundError:
        data = {}

    if discord_username in data:
        await interaction.followup.send("❌ This Discord username is already registered.")
        return

    data[discord_username] = {
        "Name": discord_username,
        "NationID": nation_id
    }

    with open("Alliance.json", "w") as f:
        json.dump(data, f, indent=4)

    await interaction.followup.send("✅ Registered successfully (manually, no validation).")
'''
@bot.tree.command(name="raws_audits", description="Audit building and raw usage per nation")
async def raws_audits(interaction: discord.Interaction, day: int):
    await interaction.response.defer(thinking=True)
    sheet = get_registration_sheet()
    rows = sheet.get_all_records()
    user_id = str(interaction.user.id)

    user_data = next((r for r in rows if str(r.get("DiscordID", "")).strip() == user_id), None)
    if not user_data:
        await interaction.followup.send("❌ You are not registered. Use `/register` first.")
        return

    async def is_banker(inter):
        return (
            any(role.name == "Government member" for role in inter.user.roles)
            or user_id == "1148678095176474678"
        )

    if not await is_banker(interaction):
        await interaction.followup.send("❌ You don't have the rights, lil bro.")
        return

    output = StringIO()
    audits_by_nation = {}
    batch_count = 0

    for idx, row in enumerate(rows):
        nation_id = str(row.get("NationID", "")).strip()
        if not nation_id:
            continue

        cities_df = graphql_cities(nation_id)
        if cities_df is None or cities_df.empty:
            output.write(f"❌ Nation ID {nation_id} - City data not found.\n\n")
            continue

        try:
            cities = cities_df.iloc[0]["cities"]
        except (KeyError, IndexError, TypeError):
            output.write(f"❌ Nation ID {nation_id} - Malformed city data.\n\n")
            continue

        projects = {
            "iron_works": 0,
            "bauxite_works": 0,
            "arms_stockpile": 0,
            "emergency_gasoline_reserve": 0
        }
        cons = {
            "iron_works": 6.12,
            "bauxite_works": 6.12,
            "arms_stockpile": 4.5,
            "emergency_gasoline_reserve": 6.12
        }
        buildings = {
            "steel_mill": 0,
            "oil_refinery": 0,
            "aluminum_refinery": 0,
            "munitions_factory": 0
        }
        suffitient = {
            "coal_mine": 0,
            "oil_well": 0,
            "lead_mine": 0,
            "iron_mine": 0,
            "bauxite_mine": 0
        }
        nu_uh = {
            "coal_mine": 3,
            "oil_well": 3,
            "lead_mine": 3,
            "iron_mine": 3,
            "bauxite_mine": 3
        }
        
        for city in cities:
            for p in projects:
                projects[p] += int(city.get(p, 0))
            for b in buildings:
                buildings[b] += int(city.get(b, 0))
            for s in suffitient:
                suffitient[s] += int(city.get(s, 0))
        
        res = get_resources(nation_id)
        if not res:
            output.write(f"❌ Nation ID {nation_id} - Resource data not found.\n\n")
            continue
        
        nation_name, _, _, _, gasoline, munitions, steel, aluminum, bauxite, lead, iron, oil, coal, _ = res
        
        required = {
            "steel_mill": {"coal": day * cons["iron_works"] * buildings["steel_mill"], "iron": day * cons["iron_works"] * buildings["steel_mill"]},
            "oil_refinery": {"oil": day * cons["emergency_gasoline_reserve"] * buildings["oil_refinery"]},
            "aluminum_refinery": {"bauxite": day * cons["bauxite_works"] * buildings["aluminum_refinery"]},
            "munitions_factory": {"lead": day * cons["arms_stockpile"] * buildings["munitions_factory"]}
        }
        
        resources = {
            "coal": coal,
            "iron": iron,
            "oil": oil,
            "bauxite": bauxite,
            "lead": lead
        }
        
        mine_map = {
            "coal": "coal_mine",
            "oil": "oil_well",
            "lead": "lead_mine",
            "iron": "iron_mine",
            "bauxite": "bauxite_mine"
        }
        
        all_ok = True
        building_lines = []
        request_lines = []
        
        for bld, reqs in required.items():
            if buildings[bld] == 0:
                continue
        
            lines = []
            fulfillment_ratios = []
        
            for res_type, req_val in reqs.items():
                had = resources[res_type]
                mine_type = mine_map[res_type]
                mine_output = suffitient[mine_type] * nu_uh[mine_type] * day
                adjusted_req = max(0, req_val - mine_output)
                ratio = had / adjusted_req if adjusted_req > 0 else 1
                fulfillment_ratios.append(ratio)
        
            min_ratio = min(fulfillment_ratios)
        
            if min_ratio >= 1:
                color = "🟢"
            elif min_ratio >= (day / 3 + day / 3) / day:
                color = "🟡"
                all_ok = False
            elif min_ratio >= (day / 3) / day:
                color = "🟠"
                all_ok = False
            else:
                color = "🔴"
                all_ok = False
        
            for res_type, req_val in reqs.items():
                had = resources[res_type]
                mine_type = mine_map[res_type]
                mine_output = suffitient[mine_type] * nu_uh[mine_type] * day
                adjusted_req = max(0, req_val - mine_output)
                missing = max(0, adjusted_req - had)
                lines.append(f"{res_type.capitalize()}: (Missing: {missing:.0f})")
                if missing > 0 and color != "🟢":
                    request_lines.append((res_type.capitalize(), missing, color))
        
            if color != "🟢":
                building_lines.append(
                    f"{bld.replace('_', ' ').title()}: {buildings[bld]} ({', '.join(lines)}) {color}"
                )
        
        if not all_ok:
            output.write(f"{nation_name} ({nation_id})\n")
            for line in building_lines:
                output.write(line + "\n")
            output.write("\n")
        
            audits_by_nation[nation_id] = {
                "nation_name": nation_name,
                "missing": request_lines,
                "color": color
            }
        
        await asyncio.sleep(2.5)

        '''batch_count += 1
        if batch_count == 30:
            await asyncio.sleep(60)
            batch_count = 0'''

    output.seek(0)
    discord_file = discord.File(fp=output, filename="raws_audit.txt")
    await interaction.followup.send("✅ Audit complete.", file=discord_file, view=RawsAuditView(output=output.getvalue(), audits=audits_by_nation))


@bot.tree.command(name="battle_sim", description="simulate a battle")
async def simulation(interaction: discord.Interaction, nation_id: str, war_type: str):
    await interaction.response.defer()
    user_id = str(interaction.user.id)
    global cached_users  # the dict version
    
    user_data = cached_users.get(user_id)  # user_id as int, no need to cast to string if keys are ints
    
    if not user_data:
        await interaction.followup.send("❌ You are not registered. Use `/register` first.")
        return
    
    own_id = str(user_data.get("NationID", "")).strip()

    if not own_id:
            await interaction.followup.send("❌ Could not find your Nation ID in the sheet.")
            return
    try:
        try:
            opponent = get_military(nation_id)
            me = get_military(own_id)
        except ValueError:
            await interaction.followup.send("❌ Failed to retrieve nation data via API.")
            return

        (
            nation_name, nation_leader, nation_score, war_policy,
            soldiers, tanks, aircraft, ships, spies, missiles, nuclear
        ) = opponent

        (
            me_name, me_leader, me_score, me_policy,
            me_soldiers, me_tanks, me_aircraft, me_ships, me_spies, me_missiles, me_nukes
        ) = me

        # Convert and calculate
        def safe_int(x):
            if isinstance(x, str):
                return int(x.replace(",", ""))
            return int(x)
        
        soldiers_int = safe_int(soldiers)
        tanks_int = safe_int(tanks)
        aircraft_int = safe_int(aircraft)
        ships_int = safe_int(ships)
        missiles_int = safe_int(missiles)
        nuclear_int = safe_int(nuclear)

        me_soldiers_int = safe_int(me_soldiers)
        me_tanks_int = safe_int(me_tanks)
        me_aircraft_int = safe_int(me_aircraft)
        me_ships_int = safe_int(me_ships)
        me_missiles_int = safe_int(me_missiles)
        me_nukes_int = safe_int(me_nukes)


        me_ground = me_soldiers_int + me_tanks_int
        enemy_ground = soldiers_int + tanks_int

        per_ground = calculation('tanks', me_ground, enemy_ground, me_policy, war_type)
        per_air = calculation('aircraft', me_aircraft_int, aircraft_int, me_policy, war_type)
        per_naval = calculation('ships', me_ships_int, ships_int, me_policy, war_type)
        per_missiles = calculation('missiles', me_missiles_int, missiles_int, me_policy, war_type)
        per_nuclear = calculation('nuclear', me_nukes_int, nuclear_int, me_policy, war_type)

        percent = round((
            per_ground["success_chance"] +
            per_air["success_chance"] +
            per_naval["success_chance"] +
            per_missiles["success_chance"] +
            per_nuclear["success_chance"]
        ) / 5, 2)

        total_loss = (
            per_ground["loss_value"] +
            per_air["loss_value"] +
            per_naval["loss_value"] +
            per_missiles["loss_value"] +
            per_nuclear["loss_value"]
        )

        total_win = (
            per_ground['win_value'] +
            per_air['win_value'] + 
            per_naval['win_value'] +
            per_missiles['win_value'] +
            per_nuclear['win_value']
        )

        msg = (
            f"> **Score:** {me_score} vs {nation_score}\n"
            f"> **War Policy:** {me_policy} vs {war_policy}\n\n"

            f"**🪖 Ground Battle (Soldiers + Tanks)**\n"
            f"> {me_ground} vs {enemy_ground} | 🎯Success Chance: {per_ground['success_chance']}% | 💥Damage Dealt: ${per_ground['win_value']} | 💸Damage Received: ${per_ground['loss_value']}\n"

            f"**✈️ Airstrike (Aircraft)**\n"
            f"> {me_aircraft_int} vs {aircraft_int} | 🎯Success Chance: {per_air['success_chance']}% | 💥Damage Dealt: ${per_air['win_value']} | 💸Damage Received: ${per_air['loss_value']}\n"

            f"**🚢 Naval Attack (Ships)**\n"
            f"> {me_ships_int} vs {ships_int} | 🎯Success Chance: {per_naval['success_chance']}% | 💥Damage Dealt: ${per_naval['win_value']} | 💸Damage Received: ${per_naval['loss_value']}\n"

            f"**🧨 Missiles**\n"
            f"> {me_missiles_int} vs {missiles_int} | 🎯Success Chance: {per_missiles['success_chance']}% | 💥Damage Dealt: ${per_missiles['win_value']} | 💸Damage Received: ${per_missiles['loss_value']}\n"

            f"**☢️ Nuclear Weapons**\n"
            f"> {me_nukes_int} vs {nuclear_int} | 🎯Success Chance: {per_nuclear['success_chance']}% | 💥Damage Dealt: ${per_nuclear['win_value']} | 💸Damage Received: ${per_nuclear['loss_value']}\n"

            f"\n🏆 ***Average Victory Chance: {percent}%***"
            f"\n💥 ***Total Damage Dealt: ${total_win}***"
            f"\n💸 ***Total Damage Received: ${total_loss}***"

        )

        embed = discord.Embed(
            title= f"🪖 **{me_name} (led by {me_leader}) vs {nation_name} (led by {nation_leader})**",
            color=discord.Color.dark_embed(),
            description=(msg)
        )
        image_url = "https://i.ibb.co/qJygzr7/Leonardo-Phoenix-A-dazzling-star-emits-white-to-bluish-light-s-2.jpg"
        embed.set_footer(text=f"Brought to you by Darkstar", icon_url=image_url)
        await interaction.followup.send(embed=embed)

    except Exception as e:
        await interaction.followup.send(f"❌ Error: {e}")


@bot.tree.command(name="nation_info", description="Info on the chosen Nation")
@app_commands.describe(
    who="The Discord member to query",
    external_id="Raw Nation ID to override user lookup (optional)"
)
async def who_nation(interaction: discord.Interaction, who: discord.Member, external_id: str = "None"):
    await interaction.response.defer()

    async def is_banker():
        return (
            any(role.name == "Government member" for role in interaction.user.roles)
            or interaction.user.id == 1148678095176474678
        )

    user_id = str(interaction.user.id)
    own_id = None

    # 🔹 If external_id is given, override own_id and skip lookup
    if external_id != "None":
        own_id = external_id.strip()

    else:
        # 🔹 If querying someone else, enforce role check
        if interaction.user.id != who.id:
            if not await is_banker():
                await interaction.followup.send("❌ You don't have the rights, lil bro.")
                return

        # 🔹 Look up the NationID from cached_users
        for discord_id, info in cached_users.items():
            if str(who.id) == discord_id:
                own_id = info.get("NationID")
                break

        if not own_id:
            await interaction.followup.send(f"❌ Could not find Nation ID for {who.mention}. They must be registered.")
            return

    # Assuming you have get_military, get_resources, get_general_data functions working
    try:
        nation_name, nation_leader, nation_score, war_policy, soldiers, tanks, aircraft, ships, spies, missiles, nuclear = get_military(own_id)
        nation_name, num_cities, food, money, gasoline, munitions, steel, aluminum, bauxite, lead, iron, oil, coal, uranium = get_resources(own_id)
        gen_data = get_general_data(own_id)

        if not gen_data:
            await interaction.followup.send("❌ Failed to fetch general data.")
            return

        (
            alliance_id,
            alliance_position,
            alliance,
            domestic_policy,
            num_cities,
            colour,
            activity,
            project,
            turns_since_last_project
        ) = gen_data

        # Format last activity time as you had it
        try:
            from datetime import datetime, timezone
            activity_dt = datetime.fromisoformat(activity)
            now = datetime.now(timezone.utc)
            delta = now - activity_dt
            if delta.total_seconds() < 60:
                activity_str = "just now"
            elif delta.total_seconds() < 3600:
                minutes = int(delta.total_seconds() // 60)
                activity_str = f"{minutes} minute{'s' if minutes != 1 else ''} ago"
            elif delta.total_seconds() < 86400:
                hours = int(delta.total_seconds() // 3600)
                activity_str = f"{hours} hour{'s' if hours != 1 else ''} ago"
            else:
                days = int(delta.total_seconds() // 86400)
                activity_str = f"{days} day{'s' if days != 1 else ''} ago"
        except Exception:
            activity_str = "Unknown"

        msg = (
            f"**📋 GENERAL INFOS:**\n"
            f"🌍 *Nation:* {nation_name} (Nation ID: `{own_id}`)\n"
            f"👑 *Leader:* {nation_leader}\n"
            f"🔛 *Active:* {activity_str}\n"
            f"🫂 *Alliance:* {alliance} (Alliance ID: `{alliance_id}`)\n"
            f"🎖️ *Alliance Position:* {alliance_position}\n"
            f"🏙️ *Cities:* {num_cities}\n"
            f"🎨 *Color Trade Bloc:* {colour}\n"
            f"📈 *Score:* {nation_score}\n"
            f"🚧 *Projects:* {project}\n"
            f"⏳ *Turn Since Last Project:* {turns_since_last_project}\n"
            f"📜 *Domestic Policy:* {domestic_policy}\n"
            f"🛡 *War Policy:* {war_policy}\n\n"

            f"**🏭 RESOURCES:**\n"
            f"🛢️ *Steel:* {steel}\n"
            f"⚙️ *Aluminum:* {aluminum}\n"
            f"💥 *Munitions:* {munitions}\n"
            f"⛽ *Gasoline:* {gasoline}\n"
            f"🛢 *Oil:* {oil}\n"
            f"⛏️ *Bauxite:* {bauxite}\n"
            f"🪨 *Coal:* {coal}\n"
            f"🔩 *Lead:* {lead}\n"
            f"🪓 *Iron:* {iron}\n"
            f"🍞 *Food:* {food}\n"
            f"💰 *Money:* ${money}\n"
            f"☢️ *Uranium:* {uranium}\n\n"

            f"**🛡 MILITARY FORCES:**\n"
            f"🪖 *Soldiers:* {soldiers}\n"
            f"🚛 *Tanks:* {tanks}\n"
            f"✈️ *Aircraft:* {aircraft}\n"
            f"🚢 *Ships:* {ships}\n"
            f"🕵️ *Spies:* {spies}\n"
            f"🚀 *Missiles:* {missiles}\n"
            f"☢️ *Nuclear Weapons:* {nuclear}"
        )

        embed = discord.Embed(
            title=f"🏳️🧑‍✈️ {nation_name}, lead by {nation_leader}",
            color=discord.Color.dark_embed(),
            description=msg
        )
        image_url = "https://i.ibb.co/qJygzr7/Leonardo-Phoenix-A-dazzling-star-emits-white-to-bluish-light-s-2.jpg"
        embed.set_footer(text="Brought to you by Darkstar", icon_url=image_url)

        nation_id = own_id
        view = NationInfoView(nation_id, embed)
        await interaction.followup.send(embed=embed, view=view)

    except Exception as e:
        await interaction.followup.send(f"❌ Error: {e}")


reasons_for_grant = [
    #app_commands.Choice(name="Warchest", value="warchest"),
    #app_commands.Choice(name="Rebuilding Stage 1", value="rebuilding_stage_1"),
   # app_commands.Choice(name="Rebuilding Stage 2", value="rebuilding_stage_2"),
    #app_commands.Choice(name="Rebuilding Stage 3", value="rebuilding_stage_3"),
    #app_commands.Choice(name="Rebuilding Stage 4", value="rebuilding_stage_4"),
    #app_commands.Choice(name="Project", value="project"),
    app_commands.Choice(name="Uranium and Food", value="Uranium and Food"),
    app_commands.Choice(name="Resources for Production", value="Resources for Production"),
]

RESOURCE_ABBR = {
    'g': '-g',  # Gasoline
    'm': '-m',  # Munition
    'a': '-a',  # Aluminium
    's': '-s',  # Steel
    'f': '-f',  # Food
    'u': '-u',  # Uranium
    'l': '-l',  # Lead
    'b': '-b',  # Bauxite
    'o': '-o',  # Oil
    'c': '-c',  # Coal
    'i': '-i',  # Iron
    '$': '-$',  # Money
}

@bot.tree.command(
    name="auto_resources_for_prod_req", 
    description="Set up auto resources request for production (bauxite, coal, iron, lead, oil)"
)
@app_commands.describe(
    coal="Amount of coal requested",
    oil="Amount of oil requested",
    bauxite="Amount of bauxite requested",
    lead="Amount of lead requested",
    iron="Amount of iron requested",
    time_period="How often would you want this requested in days",
    visual_confirmation="Type `Hypopothamus` for further confirmation"
)
async def auto_resources_for_prod_req(
    interaction: discord.Interaction,
    coal: str = "0",
    oil: str = "0",
    bauxite: str = "0",
    lead: str = "0",
    iron: str = "0",
    time_period: str = "1",
    visual_confirmation: str = ""
):
    await interaction.response.defer(ephemeral=True)
    user_id = str(interaction.user.id)

    if visual_confirmation.strip() != "Hypopothamus":
        await interaction.followup.send(
            "❌ Visual confirmation failed. Please type `Hypopothamus` exactly.", ephemeral=True
        )
        return

    user_data = cached_users.get(user_id)
    if not user_data:
        await interaction.followup.send(
            "❌ You are not registered. Please register first.", ephemeral=True
        )
        return
    
    nation_id = user_data.get("NationID", "").strip()
    if not nation_id:
        await interaction.followup.send(
            "❌ Could not find your Nation ID in the registration data.", ephemeral=True
        )
        return
    if time_period <  "1":
        await interaction.followup.send(
            "❌  The minimum is 1 day, no less", ephemeral=True
        )
        return

    sheet = get_auto_requests_sheet()
    all_rows = sheet.get_all_values()
    if not all_rows or len(all_rows) < 1:
        await interaction.followup.send(
            "❌ AutoRequests sheet is empty or not found.", ephemeral=True
        )
        return

    header = all_rows[0]
    col_index = {col: idx for idx, col in enumerate(header)}

    def parse_amount(amount):
        try:
            amount = str(amount).lower().replace(",", "").strip()
            match = re.match(r"^([\d\.]+)\s*(k|m|mil|million)?$", amount)
            if not match:
                return 0
            num, suffix = match.groups()
            num = float(num)
            if suffix in ("k",):
                return int(num * 1_000)
            elif suffix in ("m", "mil", "million"):
                return int(num * 1_000_000)
            return int(num)
        except Exception:
            return 0

    now_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

    data_to_store = {
        "DiscordID": user_id,
        "NationID": nation_id,
        "Coal": parse_amount(coal),
        "Oil": parse_amount(oil),
        "Bauxite": parse_amount(bauxite),
        "Lead": parse_amount(lead),
        "Iron": parse_amount(iron),
        "TimePeriod": time_period.strip(),
    }

    rows = all_rows[1:]
    user_row_index = None
    for idx, row in enumerate(rows, start=2):
        if len(row) > col_index["DiscordID"] and row[col_index["DiscordID"]] == user_id:
            user_row_index = idx
            break

    if user_row_index:
        for key, val in data_to_store.items():
            if key in col_index:
                sheet.update_cell(user_row_index, col_index[key] + 1, val)
        # Set LastRequested to now
        sheet.update_cell(user_row_index, col_index["LastRequested"] + 1, now_str)
        await interaction.followup.send(
            "✅ Your auto-request has been updated successfully.", ephemeral=True
        )
    else:
        new_row = []
        for col in header:
            if col == "LastRequested":
                new_row.append(now_str)
            else:
                new_row.append(data_to_store.get(col, ""))
        sheet.append_row(new_row)
        await interaction.followup.send(
            "✅ Your auto-request has been added successfully.", ephemeral=True
        )

@bot.tree.command(name="disable_auto_request", description="Disable your auto-request for key raw resources")
async def disable_auto_request(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)

    user_id = str(interaction.user.id)
    sheet = get_auto_requests_sheet()
    all_rows = sheet.get_all_values()

    if not all_rows or len(all_rows) < 2:
        await interaction.followup.send("⚠️ No auto-requests found in the sheet.", ephemeral=True)
        return

    header = all_rows[0]
    rows = all_rows[1:]

    try:
        discord_idx = header.index("DiscordID")
        tracked_resources = ["Bauxite", "Coal", "Iron", "Oil", "Lead"]
        resource_indices = [header.index(r) for r in tracked_resources]
    except ValueError as e:
        await interaction.followup.send(f"❌ Header missing: {e}", ephemeral=True)
        return

    deleted = False
    for i, row in enumerate(rows, start=2):  # start=2 for correct sheet row index
        if row[discord_idx] != user_id:
            continue

        try:
            if any(int(row[j].replace(",", "")) > 0 for j in resource_indices):
                sheet.delete_rows(i)
                deleted = True
                break
        except ValueError:
            continue  # Skip malformed rows

    if deleted:
        await interaction.followup.send("✅ Your auto-request for raw resources has been disabled.", ephemeral=True)
    else:
        await interaction.followup.send("⚠️ No active auto-request for those resources found under your account.", ephemeral=True)
        
@bot.tree.command(name="request_for_ing", description="Request a grant for another member ingame with a screenshot")
@app_commands.describe(
    nation_id="Nation ID of the person you're requesting for",
    screenshot="Screenshot proving this grant request is legitimate",
    uranium="Amount of uranium requested",
    coal="Amount of coal requested",
    oil="Amount of oil requested",
    bauxite="Amount of bauxite requested",
    lead="Amount of lead requested",
    iron="Amount of iron requested",
    steel="Amount of steel requested",
    aluminum="Amount of aluminum requested",
    gasoline="Amount of gasoline requested",
    money="Amount of money requested",
    food="Amount of food requested",
    munitions="Amount of munitions requested"
)
async def request_for_ing(
    interaction: discord.Interaction,
    nation_id: str,
    screenshot: discord.Attachment,
    uranium: str = "0",
    coal: str = "0",
    oil: str = "0",
    bauxite: str = "0",
    lead: str = "0",
    iron: str = "0",
    steel: str = "0",
    aluminum: str = "0",
    gasoline: str = "0",
    money: str = "0",
    food: str = "0",
    munitions: str = "0"
):
    await interaction.response.defer()
    user_id = str(interaction.user.id)

    try:
        if not screenshot.content_type.startswith("image/"):
            await interaction.followup.send("❌ The screenshot must be an image.", ephemeral=True)
            return

        nation_id = nation_id.strip()
        if not nation_id.isdigit():
            await interaction.followup.send("❌ Nation ID must be a number.", ephemeral=True)
            return

        nation_data = get_military(nation_id)
        if not nation_data:
            await interaction.followup.send("❌ Could not retrieve nation data.", ephemeral=True)
            return

        nation_name = nation_data[0]

        raw_inputs = {
            "Uranium": uranium,
            "Coal": coal,
            "Oil": oil,
            "Bauxite": bauxite,
            "Lead": lead,
            "Iron": iron,
            "Steel": steel,
            "Aluminum": aluminum,
            "Gasoline": gasoline,
            "Money": money,
            "Food": food,
            "Munitions": munitions,
        }

        resources = {k: parse_amount(v) for k, v in raw_inputs.items()}
        requested_resources = {k: v for k, v in resources.items() if v > 0}

        if not requested_resources:
            await interaction.followup.send("❌ You must request at least one resource.", ephemeral=True)
            return

        formatted_lines = [
            f"{resource}: {amount:,}".replace(",", ".")
            for resource, amount in requested_resources.items()
        ]
        description_text = "\n".join(formatted_lines)

        embed = discord.Embed(
            title="💰 Grant Request (ING)",
            color=discord.Color.gold(),
            description=(
                f"**Nation:** {nation_name} (`{nation_id}`)\n"
                f"**Requested by:** {interaction.user.mention}\n"
                f"**Request:**\n{description_text}\n"
                f"**Reason:** Player support (with screenshot)\n"
            )
        )
        embed.set_image(url=screenshot.url)
        image_url = "https://i.ibb.co/qJygzr7/Leonardo-Phoenix-A-dazzling-star-emits-white-to-bluish-light-s-2.jpg"
        embed.set_footer(text="Brought to you by Darkstar", icon_url=image_url)

        await interaction.followup.send(embed=embed, view=GrantView())

    except Exception as e:
        await interaction.followup.send(f"❌ An unexpected error occurred: {e}", ephemeral=True)



@bot.tree.command(name="request_miscellaneous", description="Request a custom amount of resources from the alliance bank")
@app_commands.describe(
    reason="Select the reason for your grant request.",
    uranium="Amount of uranium requested",
    coal="Amount of coal requested",
    oil="Amount of oil requested",
    bauxite="Amount of bauxite requested",
    lead="Amount of lead requested",
    iron="Amount of iron requested",
    steel="Amount of steel requested",
    aluminum="Amount of aluminum requested",
    gasoline="Amount of gasoline requested",
    money="Amount of money requested",
    food="Amount of food requested",
    munitions="Amount of munitions requested"
)
#@app_commands.choices(reason=reasons_for_grant)
async def request_grant(
    interaction: discord.Interaction,
    reason: str,
    uranium: str = "0",
    coal: str = "0",
    oil: str = "0",
    bauxite: str = "0",
    lead: str = "0",
    iron: str = "0",
    steel: str = "0",
    aluminum: str = "0",
    gasoline: str = "0",
    money: str = "0",
    food: str = "0",
    munitions: str = "0",
):
    await interaction.response.defer()
    user_id = str(interaction.user.id)

    try:
        global cached_users
        user_data = cached_users.get(user_id)

        if not user_data:
            await interaction.followup.send("❌ You are not registered. Use `/register` first.")
            return

        own_id = str(user_data.get("NationID", "")).strip()
        if not own_id:
            await interaction.followup.send("❌ Could not find your Nation ID in the sheet.", ephemeral=True)
            return

        nation_data = get_military(own_id)
        nation_name = nation_data[0]
        if reason.title() in ["Warchest", "WC", "Wc"]:
            await interaction.followup.send("❌ Don't use `/request_grant`, use `/request_warchest`", ephemeral=True)
            return
        # Parse input values
        raw_inputs = {
            "Uranium": uranium,
            "Coal": coal,
            "Oil": oil,
            "Bauxite": bauxite,
            "Lead": lead,
            "Iron": iron,
            "Steel": steel,
            "Aluminum": aluminum,
            "Gasoline": gasoline,
            "Money": money,
            "Food": food,
            "Munitions": munitions,
        }

        resources = {k: parse_amount(v) for k, v in raw_inputs.items()}
        requested_resources = {k: v for k, v in resources.items() if v > 0}

        if not requested_resources:
            await interaction.followup.send("❌ You must request at least one resource.", ephemeral=True)
            return

        formatted_lines = [
            f"{resource}: {amount:,}".replace(",", ".")
            for resource, amount in requested_resources.items()
        ]
        description_text = "\n".join(formatted_lines)

        embed = discord.Embed(
            title="💰 Grant Request",
            color=discord.Color.gold(),
            description=(
                f"**Nation:** {nation_name} (`{own_id}`)\n"
                f"**Requested by:** {interaction.user.mention}\n"
                f"**Request:**\n{description_text}\n"
                f"**Reason:** {reason.title()}\n"
            )
        )
        image_url = "https://i.ibb.co/qJygzr7/Leonardo-Phoenix-A-dazzling-star-emits-white-to-bluish-light-s-2.jpg"
        embed.set_footer(text="Brought to you by Darkstar", icon_url=image_url)

        await interaction.followup.send(embed=embed, view=GrantView())

    except Exception as e:
        await interaction.followup.send(f"❌ An unexpected error occurred: {e}", ephemeral=True)

def parse_amount(amount):
    if isinstance(amount, (int, float)):
        return amount

    amount = str(amount).lower().replace(",", "").strip()
    match = re.match(r"^([\d\.]+)\s*(k|m|mil|million)?$", amount)
    if not match:
        raise ValueError(f"Invalid amount format: {amount}")

    num, suffix = match.groups()
    num = float(num)

    if suffix in ("k",):
        return int(num * 1_000)
    elif suffix in ("m", "mil", "million"):
        return int(num * 1_000_000)
    return int(num)

def parse_duration(duration):
    duration = duration.replace('PT', '')
    hours, minutes, seconds = 0, 0, 0

    if 'H' in duration:
        hours, duration = duration.split('H')
        hours = int(hours)

    if 'M' in duration:
        minutes, duration = duration.split('M')
        minutes = int(minutes)

    if 'S' in duration:
        seconds = int(duration.replace('S', ''))

    return hours * 3600 + minutes * 60 + seconds

# --- Bot Command ---
@bot.tree.command(name="warn_maint", description="Notify users of bot maintenance (Dev only)")
async def warn_maint(interaction: discord.Interaction, time: str):
    await interaction.response.defer()
    user_id = str(interaction.user.id)

    if user_id != "1148678095176474678":
        await interaction.followup.send("You don't have the required permission level", ephemeral=True)
        return

    try:
        # YouTube API Config
        CHANNEL_ID = "UC_ID-A3YnSQXCwyIcCs9QFw"

        # Fetch latest 50 videos
        search_url = 'https://www.googleapis.com/youtube/v3/search'
        search_params = {
            'part': 'snippet',
            'channelId': CHANNEL_ID,
            'maxResults': 50,
            'order': 'date',
            'type': 'video',
            'key': YT_Key
        }
        search_response = requests.get(search_url, params=search_params)
        video_ids = [item['id']['videoId'] for item in search_response.json().get('items', []) if item['id'].get('videoId')]

        # Get video durations
        videos_url = 'https://www.googleapis.com/youtube/v3/videos'
        videos_params = {
            'part': 'contentDetails',
            'id': ','.join(video_ids),
            'key': YT_Key
        }
        videos_response = requests.get(videos_url, params=videos_params)
        shorts = [
            f"https://www.youtube.com/shorts/{item['id']}"
            for item in videos_response.json().get('items', [])
            if parse_duration(item['contentDetails']['duration']) <= 60
        ]

        # Pick a random Short
        chosen_vid = random.choice(shorts) if shorts else "https://www.youtube.com"

        # Send maintenance message
        msg = (
            f"⚠️ **Bot Maintenance Notice** ⚠️\n\n"
            f"🔧 The bot will be undergoing maintenance **until {time} (UTC +2)**.\n"
            f"❌ Please **do not** accept, deny, or copy grant codes during this time.\n"
            f"🛑 Also avoid using any of the bot's commands.\n\n"
            f"We’ll be back soon! Sorry for any inconvenience this may cause.\n"
            f"If you have questions, please ping @Sumnor.\n"
            f"P.S.: If you're bored, watch this: {chosen_vid}"
        )
        await interaction.followup.send(msg)

    except Exception as e:
        await interaction.followup.send(f"❌ Failed to send maintenance warning: `{e}`")


percent_list = [
    app_commands.Choice(name="50%", value="50%"),
    app_commands.Choice(name="100%", value="100%")
]
reasons_for_grant = [
    app_commands.Choice(name="Warchest", value="warchest"),
    app_commands.Choice(name="Rebuilding Stage 1", value="rebuilding_stage_1"),
    app_commands.Choice(name="Rebuilding Stage 2", value="rebuilding_stage_2"),
    app_commands.Choice(name="Rebuilding Stage 3", value="rebuilding_stage_3"),
    app_commands.Choice(name="Rebuilding Stage 4", value="rebuilding_stage_4"),
    app_commands.Choice(name="Project", value="project"),
]

@bot.tree.command(name="request_warchest", description="Request a  grant")
@app_commands.describe(percent="How much percent of the warchest do you want")
@app_commands.choices(percent=percent_list)
async def warchest(interaction: discord.Interaction, percent: app_commands.Choice[str]):
    await interaction.response.defer()
    global commandscalled
    commandscalled["_global"] += 1
    user_id = str(interaction.user.id)
    
    global cached_users  # the dict version
    
    user_data = cached_users.get(user_id)   # user_id as int, no need to cast to string if keys are ints
    
    if not user_data:
        await interaction.followup.send("❌ You are not registered. Use `/register` first.")
        return
    
    own_id = str(user_data.get("NationID", "")).strip()

    if not own_id:
            await interaction.followup.send("❌ Could not find your Nation ID in the sheet.")
            return


    try:
        # === API Call ===
        GRAPHQL_URL = f"https://api.politicsandwar.com/graphql?api_key={API_KEY}"
        query = f"""
        {{
          nations(id: [{own_id}]) {{
            data {{
              id
              nation_name
              num_cities
              food
              uranium
              money
              gasoline
              munitions
              steel
              aluminum
            }}
          }}
        }}
        """
        response = requests.post(
            GRAPHQL_URL,
            json={"query": query},
            headers={"Content-Type": "application/json"}
        )
        response_json = response.json()

        if "data" not in response_json or "nations" not in response_json["data"] or "data" not in response_json["data"]["nations"]:
            await interaction.followup.send("❌ Failed to fetch nation data. Please check the Nation ID or try again later.")
            return

        nation_data = response_json["data"]["nations"]["data"]

        if not nation_data:
            await interaction.followup.send("❌ Nation not found. Please try again.")
            return

        # Normalize the data
        nation = nation_data[0]
        nation_name = nation["nation_name"]
        cities = nation["num_cities"]
        food = nation["food"]
        uranium = nation["uranium"]
        money = nation["money"]
        gasoline = nation["gasoline"]
        munition = nation["munitions"]
        steel = nation["steel"]
        aluminium = nation["aluminum"]

        if any(x is None for x in [cities, food, uranium, money, gasoline, munition, steel, aluminium]):
            await interaction.followup.send("❌ Missing resource data. Please try again.")
            return

        city = int(cities)

        # Adjust per-city requirements if 50% is selected
        percent_value = percent.value.strip().lower()
        if percent_value in ["50", "50%"]:
            nr_a = 325
            nr_a_f = 1500
            nr_a_m = 500000
            nr_a_u = 20
        else:
            nr_a = 750
            nr_a_f = 3000
            nr_a_m = 1000000
            nr_a_u = 40

        # Calculate total required
        nr_a_minus = city * nr_a
        nr_a_f_minus = city * nr_a_f
        nr_a_u_minus = city * nr_a_u
        money_needed = city * nr_a_m

        # Calculate deficits
        money_n = 0
        gas_n = 0
        mun_n = 0
        ste_n = 0
        all_n = 0
        foo_n = 0
        ur_n = 0

        for res, resource_value in {
            'money': money, 'gasoline': gasoline, 'munitions': munition,
            'steel': steel, 'aluminum': aluminium, 'food': food, 'uranium': uranium
        }.items():
            if res == 'money':
                new_value = resource_value - money_needed
                money_n = 0 if new_value >= 0 else -new_value
            elif res == 'gasoline':
                new_value = resource_value - nr_a_minus
                gas_n = 0 if new_value >= 0 else -new_value
            elif res == 'munitions':
                new_value = resource_value - nr_a_minus
                mun_n = 0 if new_value >= 0 else -new_value
            elif res == 'steel':
                new_value = resource_value - nr_a_minus
                ste_n = 0 if new_value >= 0 else -new_value
            elif res == 'aluminum':
                new_value = resource_value - nr_a_minus
                all_n = 0 if new_value >= 0 else -new_value
            elif res == 'food':
                new_value = resource_value - nr_a_f_minus
                foo_n = 0 if new_value >= 0 else -new_value
            elif res == 'uranium':
                new_value = resource_value - nr_a_u_minus
                ur_n = 0 if new_value >= 0 else -new_value
        
        request_lines = []
        if money_n > 0:
            request_lines.append(f"Money: {round(money_n):,.0f}\n")
        if foo_n > 0:
            request_lines.append(f"Food: {round(foo_n):,.0f}\n")
        if ur_n > 0:
            request_lines.append(f"Uranium: {round(ur_n):,.0f}\n")
        if gas_n > 0:
            request_lines.append(f"Gasoline: {round(gas_n):,.0f}\n")
        if mun_n > 0:
            request_lines.append(f"Munitions: {round(mun_n):,.0f}\n")
        if ste_n > 0:
            request_lines.append(f"Steel: {round(ste_n):,.0f}\n")
        if all_n > 0:
            request_lines.append(f"Aluminum: {round(all_n):,.0f}")
        
        description_text = ''.join(request_lines).strip()
        
        if not description_text:
            await interaction.followup.send(
                f"You already possess all needed resources for a {percent_value} warchest",
                ephemeral=True
            )
            return

        embed = discord.Embed(
            title="💰 Grant Request",
            color=discord.Color.gold(),
            description=(
                f"**Nation:** {nation_name} (`{own_id}`)\n"
                f"**Requested by:** {interaction.user.mention}\n"
                f"**Request:**\n{description_text}\n"
                f"**Reason:** Warchest\n"
            )
        )
        image_url = "https://i.ibb.co/qJygzr7/Leonardo-Phoenix-A-dazzling-star-emits-white-to-bluish-light-s-2.jpg"
        embed.set_footer(text=f"Brought to you by Darkstar", icon_url=image_url)
        await interaction.followup.send(embed=embed, view=GrantView())
    except Exception as e:
        await interaction.followup.send(f"❌ Error: {e}")


user_nation_ids = {
    "lordygon": 459160,
    "patrickrickrickpatrick": 636722,
    "masteraced": 365325,
    "vladmier1": 510930,
    "goswat14542308": 683429,
    "darko50110": 671583,
    "arstotzka111": 605608,
    "hypercombatman": 236312,
    ".technostan": 665217,
    "wholelottawar": 635047,
    "aeternite": 619412,
    "speckgard": 631277,
    "fishpool0211": 510895,
    "micmou123": 277286,
    "tymon_pik": 615360,
    "cookie_xdsorry": 648675,
    "jhon_tachanka_doe": 538189,
    "pindakaas07": 613818,
    "ellianmarkwell": 646388,
    "sabtien123": 447228,
    "kaelkek": 614369,
    "lemyrzin": 650657,
    "brutallich": 259382,
    "varant1x": 646579,
    "chevdev98": 680527,
    "rogue__5": 673641,
    "peoplerep_the_great": 554863,
    "iam_jinxed": 671871,
    "bendover995": 667252,
    "scottyboi3413": 679028,
    "1khri": 679562,
    "acoldlinks": 615210,
    "bruhbaboon": 683575,
    "miranacious_17083": 680196,
    ".nygi": 677500,
    "skryni": 688146,
    "sayyedistan.": 685174,
    "jonas9629": 433465,
    "dietc0ke": 622443,
    "chrissyno": 551321,
    "bigmoney89": 649719,
    "man.is.80090": 625208,
    "actuallyprille": 608492,
    "fumzy0207": 652466,
    "georgewashington1111": 645621,
    "ticklemctickleson": 607513,
    "r0b3rt11": 646757,
    "supersmart_09262": 684684,
    "papang0001": 690323,
    "gtag4ever": 647486,
    "jiradin": 656339,
    "pzoez2": 547638,
}

@bot.tree.command(name="help", description="Get the available commands")
async def help(interaction: discord.Interaction):
    await interaction.response.defer()
    user_id = str(interaction.user.id)
    
    global cached_users  # the dict version
    
    user_data = cached_users.get(user_id)   # user_id as int, no need to cast to string if keys are ints
    
    if not user_data:
        await interaction.followup.send("❌ You are not registered. Use `/register` first.")
        return
    
    own_id = str(user_data.get("NationID", "")).strip()

    if not own_id:
            await interaction.followup.send("❌ Could not find your Nation ID in the sheet.")
            return
    register_description = (
        "Register yourself using this command to use the *many amazing* freatures of this bot, developed by **<@722094493343416392>**\n"
        "The command is /register nation_id: 680627\n"
        "**Note:** The bot only works if you're registered\n"
    )
    warchest_desc = (
        "Calculates the needed amount of materials for a warchest and requests those\n"
        "Once your request was approved, it will inform you by pinging you\n"
        "The command is /request_warchest percent: 50% or 100%\n"
    )
    warchest_audit_desc = (
        "Calculates the needed amount of materials for a warchest and generates a message to send to the audited user (no ping)\n"
        "The command is /warchest_audit who: @sumnor_the_lazy\n"
    )
    war_losses_desc = (
        "Get the war details for your last few wars\n"
        "The command is /war_losses nation_id: 680627, wars_count: 20\n"
    )
    war_losses_alliance_desc = (
        "Get the war details for the alliance\n"
        "The command is /war_losses_alliance alliance_id: 10259, war_count: 150, money_more_detail: False\n"
    )
    res_in_m_desc = (
        "Get the worth of the Alliance and their members with a graph\n"
        "The command is /res_in_m_for_a mode: Hourly, scale: Billions\n "
    )
    res_detail_desc = (
        "Get the exact number of resources and money + the total of the members of the alliance\n"
        "The command is /res_details_for_alliance"
    )
    mmr_audit_desc = (
        "Get the MMR and the military of the chosen person, with buttons to generate messages to whatever is wrong\n"
        "The command is /mmr_audit who: @sumnor_the_lazy\n"
    )
    member_activity_desc = (
        "Get a Pie Chart for the member activity\n"
        "The command is /member_activity\n"
    )
    send_message_to_channels_desc = (
        "Send a message to a few of you chosen channels\n"
        "The command is /send_message_to_channels channels: #channel message: Pookie :heart:\n"
    )
    dm_user_desc = (
        "Dm one user who is in the server\n"
        "The command is /dm_user who: @masteraced message: Hello ~Pookie :heart:~\n"
    )
    battle_sim_desc = (
        "Generates an approximate battle based on the military of both nations and shows approximate win-chance\n"
        "The command is /battle_sim nation_id: 680627, war_type: Raid\n"
    )
    my_nation_desc = (
        "Shows some general information about the chosen person's nation\n"
        "The command is /nation_info who: @sumnor_the_lazy\n"
    )
    request_grant_desc = (
        "Requests the requested materials. This command is to make the EA departments job easier\n"
        "The command is /request_grant food: 18mil, uranium: 6k, bauxite: 980, ..., reason: Resources for Production, ...\n"
    )
    request_city_desc = (
        "Calculates the approximate cost to buy the requested cities and, if wanted, requests them\n"
        "The command is /request_city current_city: 10, target_city: 15\n"
        "**Note**: On bigger requests the cost inflates a bit\n"
    )
    request_infra_grant_desc = (
        "Calculates the approximate cost of the wanted infra and, if wanted, requests them\n"
        "The command is /request_infra_cost current_infra: 10, target_infra: 1500, city_amount: 10 or if you want it automatically calculated /request_infra_grant target_infra: 2000. This will calculate the cost to get all your cities to 2k infra\n"
        "**Note**: On bigger requests the cost inflates a bit\n"
    )
    request_project_desc = (
        "Calculates the needed materials and money to get the wanted project and, if wanted, requests it\n"
        "The command is /request_project project: Moon Landing\n"
    )
    bug_rep_desc = (
        "Report a bug"
        "The command is /bug_report bug: insert bug report here\n"
    )
    gov_msg = (
        "\n***`/register`:***\n"
        f"{register_description}"
        "\n***`/request_warchest`:***\n"
        f"{warchest_desc}"
        "\n***`/warchest_audit`:***\n"
        f"{warchest_audit_desc}"
        "\n***`/war_losses`:***\n"
        f"{war_losses_desc}"
        "\n***`/war_losses_alliance`:***\n"
        f"{war_losses_alliance_desc}"
        "\n***`/res_in_m_for_a`:***\n"
        f"{res_in_m_desc}"
        "\n***`/res_details_for_alliance`:***\n"
        f"{res_detail_desc}"
        "\n***`/mmr_audit`:***\n"
        f"{mmr_audit_desc}"
        "\n***`/member_activity`:***\n"
        f"{member_activity_desc}"
        "\n***`/send_message_to_channels`:***\n"
        f"{send_message_to_channels_desc}"
        "\n***`/dm_user`:***\n"
        f"{dm_user_desc}"
        "\n***`/battle_sim`:***\n"
        f"{battle_sim_desc}"
        "\n***`/nation_info`:***\n"
        f"{my_nation_desc}"
        "\n***`/request_grant`:***\n"
        f"{request_grant_desc}"
        "\n***`/request_city`:***\n"
        f"{request_city_desc}"
        "\n***`/request_infra_grant`:***\n"
        f"{request_infra_grant_desc}"
        "\n***`/request_project`:***\n"
        f"{request_project_desc}"
    )
    gov_mssg = discord.Embed(
        title="List of the commands (including the government ones):",
        color=discord.Color.purple(),
        description=gov_msg
    )
    image_url = "https://i.ibb.co/qJygzr7/Leonardo-Phoenix-A-dazzling-star-emits-white-to-bluish-light-s-2.jpg"
    gov_mssg.set_footer(text=f"Brought to you by Darkstar", icon_url=image_url)

    norm_msg = (
        "\n***`/register`:***\n"
        f"{register_description}"
        "\n***`/request_warchest`:***\n"
        f"{warchest_desc}"
        "\n***`/war_losses`:***\n"
        f"{war_losses_desc}"
        "\n***`/war_losses_alliance`:***\n"
        f"{war_losses_alliance_desc}"
        "\n***`/battle_sim`:***\n"
        f"{battle_sim_desc}"
        "\n***`/nation_info`:***\n"
        f"{my_nation_desc}"
        "\n***`/request_grant`:***\n"
        f"{request_grant_desc}"
        "\n***`/request_city`:***\n"
        f"{request_city_desc}"
        "\n***`/request_infra_grant`:***\n"
        f"{request_infra_grant_desc}"
        "\n***`/request_project`:***\n"
        f"{request_project_desc}"
    )

    norm_mssg = discord.Embed(
        title="List of the commands:",
        color=discord.Color.blue(),
        description=norm_msg
    )
    image_url = "https://i.ibb.co/qJygzr7/Leonardo-Phoenix-A-dazzling-star-emits-white-to-bluish-light-s-2.jpg"
    norm_mssg.set_footer(text=f"Brought to you by Darkstar", icon_url=image_url)
    async def is_high_power(interaction):
        return (
            any(role.name == "Government member" for role in interaction.user.roles)
            or str(interaction.user.id) == "1148678095176474678"
        )
    
    if not await is_high_power(interaction):
        await interaction.followup.send(embed=norm_mssg)
    else:
        await interaction.followup.send(embed=gov_mssg)


@bot.tree.command(name="request_city", description="Calculate cost for upgrading from current city to target city")
@app_commands.describe(current_cities="Your current number of cities", target_cities="Target number of cities")
async def request_city(interaction: discord.Interaction, current_cities: int, target_cities: int):
    await interaction.response.defer()
    user_id = str(interaction.user.id)
    commandscalled[user_id] = commandscalled.get(user_id, 0) + 1
    try:
        global cached_users  # the dict version
        
        user_data = cached_users.get(user_id)  # user_id as int, no need to cast to string if keys are ints
        
        if not user_data:
            await interaction.followup.send("❌ You are not registered. Use `/register` first.")
            return
        
        own_id = str(user_data.get("NationID", "")).strip()
    except Exception as e:
        print(f"Error checking registration: {e}")
        await interaction.followup.send("🚫 Error checking registration. Please try again later.")
        return
    if target_cities <= current_cities:
        await interaction.followup.send("❌ Target cities must be greater than current cities.")
        return
    elif current_cities <= 0:
        await interaction.followup.send("❌ Current cities must be greater than 0.")
        return        

    datta = get_resources(own_id)
    nation_name = datta[0]
    total_cost = 0
    cost_details = []
    top20Average = 41.47  # This is static, you can change this

    def compute_city_cost(cityToBuy: int, top20Average: float) -> float:
        # Static costs for cities 2–10
        static_costs = {
            2: 400_000,
            3: 900_000,
            4: 1_600_000,
            5: 2_500_000,
            6: 3_600_000,
            7: 4_900_000,
            8: 6_400_000,
            9: 8_100_000,
            10: 10_000_000,
        }

        if cityToBuy < 11:
            return static_costs.get(cityToBuy, 0)

        delta = cityToBuy - (top20Average / 4)
        clause_1 = (100_000 * (delta ** 3)) + (150_000 * delta) + 75_000
        clause_2 = max(clause_1, (cityToBuy ** 2) * 100_000)

        return clause_2

    def round_up_to_nearest(value: float, round_to: float) -> float:
        """
        Round the value up to the nearest specified round_to value.
        """
        return math.ceil(value / round_to) * round_to

    def get_rounding_multiple(city_number: int) -> int:
        """
        Returns the appropriate rounding multiple based on the city number.
        For city numbers 30, 40, 50, etc.
        """
        if city_number < 30:
            return 1_000_000  # Round to nearest 1 million for cities 17 to 29
        elif city_number < 60:
            return 5_000_000  # Round to nearest 5 million for cities 30 to 59
        elif city_number < 100:
            return 11_000_000  # Round to nearest 11 million for cities 60 to 99
        else:
            return 20_000_000  # Round to nearest 20 million for cities 100+

    for i in range(current_cities + 1, target_cities + 1):
        cost = compute_city_cost(i, top20Average)
        user_id = interaction.user.id

        # Apply the rounding logic based on the new rounding criteria
        rounding_multiple = get_rounding_multiple(i)
        
        # Apply rounding to the nearest multiple depending on the city number
        if i >= 30:
            cost = round_up_to_nearest(cost, rounding_multiple)

        total_cost += cost
        cost_details.append(f"City {i}: ${cost:,.2f}")

    embed = discord.Embed(
        title="🏙️ City Upgrade Cost",
        color=discord.Color.green(),
        description="\n".join(cost_details)
    )
    embed.add_field(name="Total Cost:", value=f"${total_cost:,.0f}", inline=False)
    image_url = "https://i.ibb.co/qJygzr7/Leonardo-Phoenix-A-dazzling-star-emits-white-to-bluish-light-s-2.jpg"
    embed.set_footer(text="Brought to you by Darkstar", icon_url=image_url)

    await interaction.followup.send(
        embed=embed,
        view=BlueGuy(category="city", data={
            "nation_name": nation_name,
            "nation_id": own_id,
            "from": current_cities,
            "city_num": target_cities,
            "total_cost": total_cost,
            "person": user_id
        })
        
                    )

def get_city_data(nation_id: str) -> list[dict]:
    GRAPHQL_URL = f"https://api.politicsandwar.com/graphql?api_key={API_KEY}"

    query = f"""
    {{
      cities(nation_id: {nation_id}) {{
        data {{
          name
          infrastructure
        }}
      }}
    }}
    """

    response = requests.post(
        GRAPHQL_URL,
        json={"query": query},
        headers={"Content-Type": "application/json"}
    )
    try:
        response_json = response.json()
        city_data = response_json.get("data", {}).get("cities", {}).get("data", [])
    except Exception:
        city_data = []

    if not city_data:
        return []

    return [{"name": city.get("name", "Unknown"), "infra": city.get("infrastructure", 0)} for city in city_data]

def calculate_infra_cost_for_range(start_infra: int, end_infra: int) -> float:
    """
    Calculate cost for upgrading infrastructure from start_infra to end_infra for a single city,
    handling partial tiers correctly.
    """
    tiers = [
        (0, 100, 30_000),
        (100, 200, 30_000),
        (200, 300, 40_000),
        (300, 400, 70_000),
        (400, 500, 100_000),
        (500, 600, 150_000),
        (600, 700, 200_000),
        (700, 800, 280_000),
        (800, 900, 370_000),
        (900, 1000, 470_000),
        (1000, 1100, 580_000),
        (1100, 1200, 710_000),
        (1200, 1300, 850_000),
        (1300, 1400, 1_000_000),
        (1400, 1500, 1_200_000),
        (1500, 1600, 1_400_000),
        (1600, 1700, 1_600_000),
        (1700, 1800, 1_800_000),
        (1800, 1900, 2_000_000),
        (1900, 2000, 2_300_000)
    ]
    
    total_cost = 0.0
    for low, high, cost_per_100 in tiers:
        if start_infra >= high or end_infra <= low:
            continue

        segment_start = max(start_infra, low)
        segment_end = min(end_infra, high)

        portion = (segment_end - segment_start) / 100
        total_cost += portion * cost_per_100

    return total_cost

def calculate_total_infra_cost(start_infra: int, end_infra: int, num_cities: int) -> float:
    """
    Calculate the total cost to upgrade multiple cities from start_infra to end_infra.
    Applies `calculate_infra_cost_for_range` for each city and multiplies by the number of cities.
    """
    cost_per_city = calculate_infra_cost_for_range(start_infra, end_infra)
    return cost_per_city * num_cities

@bot.tree.command(name="request_infra_cost", description="Calculate infrastructure upgrade cost (single city, all cities, or custom)")
@app_commands.describe(
    target_infra="Target infrastructure level (max 2000)",
    current_infra="Your current infrastructure level (manual mode only)",
    city_amount="Number of cities to upgrade (manual mode only)",
    auto_calculate="Automatically fetch and calculate cost for all cities",
    city_name="Calculate for a specific city by name"
)
async def infra_upgrade_cost(
    interaction: discord.Interaction,
    target_infra: int,
    current_infra: int = 0,
    city_amount: int = 1,
    auto_calculate: bool = True,
    city_name: str = None
):
    await interaction.response.defer()
    user_id = str(interaction.user.id)

    if target_infra > 2000:
        await interaction.followup.send("❌ Target infrastructure above 2000 is not supported.(*** Personal Contribution by `@patrickrickrickpatrick` ***)")
        return

    # 🔹 Validate registration
    try:
        global cached_users  # the dict version
        
        user_data = cached_users.get(user_id)  # user_id as int, no need to cast to string if keys are ints
        
        if not user_data:
            await interaction.followup.send("❌ You are not registered. Use `/register` first.")
            return
        
        own_id = str(user_data.get("NationID", "")).strip()
        if not own_id:
            await interaction.followup.send("❌ Could not find your Nation ID in the sheet.")
            return
    except Exception as e:
        await interaction.followup.send(f"❌ Failed to access your data: {e}")
        return

    # 🔹 Retrieve city data
    city_data = get_city_data(own_id)
    if not city_data:
        await interaction.followup.send("❌ Could not retrieve city data for your nation.")
        return

    nation_data = get_resources(own_id)
    nation_name = nation_data[0]
    nation_id = own_id
    if city_name:
        city = next((c for c in city_data if c["name"].lower() == city_name.lower()), None)
        if not city:
            await interaction.followup.send(f"❌ Could not find city named '{city_name}' in your nation.")
            return

        current = city["infra"]
        if current >= target_infra:
            await interaction.followup.send(f"❌ '{city_name}' already has infrastructure >= target.")
            return

        cost = calculate_infra_cost_for_range(current, target_infra)
        if cost > 900_000:
            cost = math.ceil(cost / 10_000) * 10_000
        user_id = interaction.user.id
        data = {
            "nation_name": nation_name,
            "nation_id": nation_id,
            "from": current_infra,
            "infra": target_infra,
            "ct_count": city_amount,
            "total_cost": cost,
            "person": user_id
        }

        embed = discord.Embed(
            title=f"Upgrade Cost for {city_name}",
            color=discord.Color.gold(),
            description=f"Upgrade from {current} to {target_infra}\nEstimated Cost: **${cost:,.0f}**"
        )
        embed.set_footer(text="Brought to you by Darkstar\nPersonal Contribution by <@1026284133481189388>", icon_url="https://i.ibb.co/qJygzr7/Leonardo-Phoenix-A-dazzling-star-emits-white-to-bluish-light-s-2.jpg")
        await interaction.followup.send(
            embed=embed,
            view=BlueGuy(category="infra", data=data)
        )
        return

    # 🔹 Auto calculate for all cities
    if auto_calculate:
        total_cost = 0
        description_lines = []

        for city in city_data:
            name = city["name"]
            current = city["infra"]
            if current >= target_infra:
                continue
            cost = calculate_infra_cost_for_range(current, target_infra)
            total_cost += cost
            description_lines.append(f"**{name}:** ${cost:,.0f}")
            city_amount += 1

        if not description_lines:
            await interaction.followup.send("✅ All cities are already at or above the target infrastructure.")
            return
        user_id = interaction.user.id
        rounded_total_cost = int(math.ceil(total_cost / 1_000_000.0)) * 1_000_000
        data = {
            "nation_name": nation_name,
            "nation_id": nation_id,
            "from": current_infra,
            "infra": target_infra,
            "ct_count": city_amount,
            "total_cost": rounded_total_cost,
            "person": user_id
        }
        
        embed = discord.Embed(
            title=f"🛠️ Infrastructure Upgrade Cost for {len(description_lines)} City(ies)",
            color=discord.Color.green(),
            description="\n".join(description_lines) + f"\n\n**Total estimated cost(rounded up to the nearest million): ${rounded_total_cost:,.0f}**"
        )
        embed.set_footer(text="Brought to you by Darkstar\nPersonal Contribution by @patrickrickrickpatrick", icon_url="https://i.ibb.co/qJygzr7/Leonardo-Phoenix-A-dazzling-star-emits-white-to-bluish-light-s-2.jpg")
        await interaction.followup.send(
            embed=embed,
            view=BlueGuy(category="infra", data=data)
        )
        return

    # 🔹 Manual input fallback
    if current_infra is None:
        current_infra = 0
    if city_amount is None:
        city_amount = 1
    if target_infra <= current_infra:
        await interaction.followup.send("❌ Target infrastructure must be greater than current infrastructure.")
        return

    total_cost = calculate_total_infra_cost(current_infra, target_infra, city_amount)
    if total_cost > 900_000:
        rounded_total_cost = math.ceil(total_cost / 100_000) * 100_000
        
    data = {
            "nation_name": nation_name,
            "nation_id": nation_id,
            "from": current_infra,
            "infra": target_infra,
            "ct_count": city_amount,
            "total_cost": rounded_total_cost,
            "person": user_id
        }


    embed = discord.Embed(
        title="🛠️ Infrastructure Upgrade Cost",
        color=discord.Color.green(),
        description=f"From `{current_infra}` to `{target_infra}` for `{city_amount}` city(ies)\nEstimated Cost: **${total_cost:,.0f}**"
    )
    embed.set_footer(text="Brought to you by Darkstar", icon_url="https://i.ibb.co/qJygzr7/Leonardo-Phoenix-A-dazzling-star-emits-white-to-bluish-light-s-2.jpg")
    await interaction.followup.send(embed=embed, view=BlueGuy(category="infra", data=data))


list_of_em = [
    app_commands.Choice(name="Infrastructure Projects", value="infrastructure_projects"),
    app_commands.Choice(name="Space Projects", value="space_projects"),
    app_commands.Choice(name="Defense Projects", value="defense_projects"),
    app_commands.Choice(name="Military Projects", value="military_projects"),
    app_commands.Choice(name="Espionage Projects", value="espionage_projects"),
    app_commands.Choice(name="Research Projects", value="research_projects"),
    app_commands.Choice(name="Economic Projects", value="economic_projects"),
    app_commands.Choice(name="Industry Boosters", value="industry_boosters"),
    app_commands.Choice(name="Domestic Affairs", value="domestic_affairs"),
    app_commands.Choice(name="Commerce Enhancements", value="commerce_enhancements"),
    app_commands.Choice(name="Login Bonus", value="login_bonus")
]

all_names = [
    "Center for Civil Engineering",
    "Advanced Engineering Corps",
    "Arable Land Agency",
    "Space Program",
    "Moon Landing",
    "Mars Landing",
    "Telecommunications Satellite",
    "Guiding Satellite",
    "Nuclear Research Facility",
    "Nuclear Launch Facility",
    "Missile Launch Pad",
    "Vital Defense System",
    "Iron Dome",
    "Fallout Shelter",
    "Arms Stockpile",
    "Military Salvage",
    "Propaganda Bureau",
    "Intelligence Agency",
    "Spy Satellite",
    "Surveillance Network",
    "Clinical Research Center",
    "Recycling Initiative",
    "Research and Development Center",
    "Green Technologies",
    "Pirate Economy",
    "Advanced Pirate Economy",
    "International Trade Center",
    "Ironworks",
    "Bauxiteworks",
    "Emergency Gasoline Reserve",
    "Mass Irrigation",
    "Uranium Enrichment Program",
    "Government Support Agency",
    "Bureau of Domestic Affairs",
    "Specialized Police Training Program",
    "Activity Center"
]

aller_names = [app_commands.Choice(name=name, value=name) for name in all_names]

project_costs = {
    "Infrastructure Projects": {
        "Center for Civil Engineering": {"Money": 3000000, "Oil": 1000, "Iron": 1000, "Bauxite": 1000},
        "Advanced Engineering Corps": {"Money": 50000000, "Munitions": 10000, "Gasoline": 10000, "Uranium": 1000},
        "Arable Land Agency": {"Money": 3000000, "Coal": 1500, "Lead": 1500},
    },
    "Space Projects": {
        "Space Program": {"Money": 50000000, "Aluminum": 25000},
        "Moon Landing": {"Money": 50000000, "Oil": 5000, "Aluminum": 5000, "Munitions": 5000, "Steel": 5000, "Gasoline": 5000, "Uranium": 10000},
        "Mars Landing": {"Money": 200000000, "Oil": 20000, "Aluminum": 20000, "Munitions": 20000, "Steel": 20000, "Gasoline": 20000, "Uranium": 20000},
        "Telecommunications Satellite": {"Money": 300000000, "Oil": 10000, "Aluminum": 10000, "Iron": 10000, "Uranium": 10000},
        "Guiding Satellite": {"Money": 200000000, "Munitions": 40000, "Uranium": 40000, "Gasoline": 40000, "Aluminum": 40000, "Steel": 20000},
    },
    "Defense Projects": {
        "Nuclear Research Facility": {"Money": 75000000, "Uranium": 5000, "Gasoline": 5000, "Aluminum": 5000},
        "Nuclear Launch Facility": {"Money": 750000000, "Uranium": 50000, "Gasoline": 50000, "Aluminum": 50000},
        "Missile Launch Pad": {"Money": 15000000, "Munitions": 5000, "Gasoline": 5000, "Aluminum": 5000},
        "Vital Defense System": {"Money": 40000000, "Steel": 5000, "Aluminum": 5000, "Munitions": 5000, "Gasoline": 5000},
        "Iron Dome": {"Money": 15000000, "Munitions": 5000},
        "Fallout Shelter": {"Money": 25000000, "Food": 100000, "Lead": 10000, "Aluminum": 15000, "Steel": 10000},
    },
    "Military Projects": {
        "Military Doctrine": {"Money": 10000000, "Steel": 10000,  "Aluminum": 10000, "Munitions": 10000, "Gasoline": 10000},
        "Arms Stockpile": {"Money": 10000000, "Coal": 500, "Iron": 500, "Oil": 500, "Bauxite": 500, "Lead": 500},
        "Military Salvage": {"Money": 20000000, "Aluminum": 5000, "Steel": 5000, "Gasoline": 5000},
        "Propaganda Bureau": {"Money": 10000000, "Gasoline": 2000, "Munitions": 2000, "Aluminum": 2000, "Steel": 2000},
    },
    "Espionage Projects": {
        "Intelligence Agency": {"Money": 5000000, "Steel": 500, "Gasoline": 500},
        "Spy Satellite": {"Money": 20000000, "Oil": 10000, "Bauxite": 10000, "Iron": 10000, "Lead": 10000, "Coal": 10000},
        "Surveillance Network": {"Money": 50000000, "Aluminum": 50000, "Bauxite": 15000, "Iron": 15000, "Lead": 15000, "Coal": 15000},
    },
    "Research Projects": {
        "Military Research Center": {"Money": 100000000, "Steel": 10000,  "Aluminum": 10000, "Munitions": 10000, "Gasoline": 10000},
        "Clinical Research Center": {"Money": 10000000, "Food": 100000},
        "Recycling Initiative": {"Money": 10000000, "Food": 100000},
        "Research and Development Center": {"Money": 50000000, "Aluminum": 5000, "Food": 100000, "Uranium": 1000},
        "Green Technologies": {"Money": 50000000, "Food": 100000, "Aluminum": 10000, "Iron": 10000, "Oil": 10000},
    },
    "Economic Projects": {
        "Pirate Economy": {"Money": 25000000, "Coal": 7500, "Iron": 7500, "Oil": 7500, "Bauxite": 7500, "Lead": 7500},
        "Advanced Pirate Economy": {"Money": 50000000, "Coal": 10000, "Iron": 10000, "Oil": 10000, "Bauxite": 10000, "Lead": 10000},
        "International Trade Center": {"Money": 50000000, "Aluminum": 10000},
    },
    "Industry Boosters": {
        "Ironworks": {"Money": 10000000, "Coal": 500, "Iron": 500, "Oil": 500, "Bauxite": 500, "Lead": 500},
        "Bauxiteworks": {"Money": 10000000, "Coal": 500, "Iron": 500, "Oil": 500, "Bauxite": 500, "Lead": 500},
        "Emergency Gasoline Reserve": {"Money": 10000000, "Coal": 500, "Iron": 500, "Oil": 500, "Bauxite": 500, "Lead": 500},
        "Mass Irrigation": {"Money": 10000000, "Food": 50000, "Coal": 500, "Iron": 500, "Oil": 500, "Bauxite": 500, "Lead": 500},
        "Uranium Enrichment Program": {"Money": 25000000, "Uranium": 2500, "Coal": 500, "Iron": 500, "Oil": 500, "Bauxite": 500, "Lead": 500},
    },
    "Domestic Affairs": {
        "Government Support Agency": {"Money": 20000000, "Aluminum": 10000, "Food": 200000},
        "Bureau of Domestic Affairs": {"Money": 20000000, "Food": 500000, "Coal": 8000, "Bauxite": 8000, "Lead": 8000, "Iron": 8000, "Oil": 8000},
        "Specialized Police Training Program": {"Money": 50000000, "Food": 250000, "Aluminum": 5000},
    },
    "Commerce Enhancements": {
        "Telecommunications Satellite": {"Money": 300000000, "Oil": 10000, "Aluminum": 10000, "Iron": 10000, "Uranium": 10000},
        "International Trade Center": {"Money": 50000000, "Aluminum": 10000},
    },
    "Login Bonus": {
        "Activity Center": {"Money": 500000, "Food": 1000},
    }
}

def get_materials(project_name):
    for category, projects in project_costs.items():
        if project_name in projects:
            return projects[project_name]
    return None  # Project not found

@bot.tree.command(name="request_project", description="Fetch resources for a project")
#@app_commands.choices(project_name=aller_names)
@app_commands.describe(project_name="Name of the project", tech_advancement="Is Technological Advancement active?")
async def request_project(interaction: Interaction, project_name: str, tech_advancement: bool = False):
    await interaction.response.defer()
    user_id = str(interaction.user.id)

    try:
        global cached_users  # the dict version
        
        user_data = cached_users.get(user_id)  # user_id as int, no need to cast to string if keys are ints
        
        if not user_data:
            await interaction.followup.send("❌ You are not registered. Use `/register` first.")
            return
        
        own_id = str(user_data.get("NationID", "")).strip()

        if not own_id:
            await interaction.followup.send("❌ Could not find your Nation ID in the sheet.")
            return

    except Exception as e:
        await interaction.followup.send(f"❌ Failed to access your data: {e}")
        return

    nation_data = get_resources(own_id)
    nation_name = nation_data[0] if nation_data else "?"
    mats = get_materials(project_name)

    if mats:
        if tech_advancement:
            for mat in mats:
                mats[mat] = mats[mat] * 0.95

        embed = discord.Embed(
            title=f"***Cost for {project_name.title()}***",
            color=discord.Color.blue()
        )

        embed.description = (
            f"**Nation:** {nation_name} (`{own_id}`)\n"
            f"**Request:**\n" +
            "\n".join([f"{mat}: {amount:,.0f}" for mat, amount in mats.items()]) +
            f"\n\n**Requested by:** {interaction.user.mention}\n"
            f"**Reason:**\nBuild project: {project_name.title()}"
        )
        user_id = interaction.user.id

        await interaction.followup.send(
            embed=embed,
            view=BlueGuy(category="project", data={"nation_name": nation_name, "nation_id": own_id, "project_name": project_name, "materials": mats, "person": user_id})
        )
    else:
        await interaction.followup.send("❌ Project not found.")

@bot.tree.command(name="dm_user", description="DM a user by mentioning them")
@app_commands.describe(
    user="Mention the user to DM",
    message="The message to send"
)
async def dm_user(interaction: discord.Interaction, user: discord.User, message: str):
    await interaction.response.defer(ephemeral=True)
    user_id = str(interaction.user.id)
    
    global cached_users  # the dict version
    
    user_data = cached_users.get(user_id)   # user_id as int, no need to cast to string if keys are ints
    
    if not user_data:
        await interaction.followup.send("❌ You are not registered. Use `/register` first.")
        return
    
    own_id = str(user_data.get("NationID", "")).strip()

    if not own_id:
            await interaction.followup.send("❌ Could not find your Nation ID in the sheet.")
            return
    async def is_banker(interaction):
        return (
        any(role.name == "Government member" for role in interaction.user.roles)
            or str(interaction.user.id) == "1148678095176474678"
        )

    if not await is_banker(interaction):
        await interaction.followup.send("❌ You don't have the rights, lil bro.")
        return
    better_msg = message.replace(")(", "\n")
    try:
        await user.send(better_msg)
        await interaction.followup.send(f"✅ Sent DM to {user.mention}")

        # Save to Google Sheet
        save_dm_to_sheet(interaction.user.name, user.name, better_msg)

    except discord.Forbidden:
        await interaction.followup.send(f"❌ Couldn't send DM to {user.mention} (they may have DMs disabled).")
    except Exception as e:
        await interaction.followup.send(f"❌ An error occurred: {e}")



@bot.tree.command(name="send_message_to_channels", description="Send a message to multiple channels by their IDs")
@app_commands.describe(
    channel_ids="Space-separated list of channel IDs (e.g. 1319746766337478680 1357611748462563479)",
    message="The message to send to the channels"
)
async def send_message_to_channels(interaction: discord.Interaction, channel_ids: str, message: str):
    await interaction.response.defer()
    user_id = str(interaction.user.id)
    
    global cached_users  # the dict version
    
    user_data = cached_users.get(user_id)   # user_id as int, no need to cast to string if keys are ints
    
    if not user_data:
        await interaction.followup.send("❌ You are not registered. Use `/register` first.")
        return
    
    own_id = str(user_data.get("NationID", "")).strip()

    if not own_id:
            await interaction.followup.send("❌ Could not find your Nation ID in the sheet.")
            return
    # Clean and split channel IDs
    channel_ids_list = [cid.strip().replace("<#", "").replace(">", "") for cid in channel_ids.split()]

    # Permission check function
    async def is_banker(interaction):
        return (
            any(role.name == "Government member" for role in interaction.user.roles)
            or str(interaction.user.id) == "1148678095176474678"
        )

    if not await is_banker(interaction):
        await interaction.followup.send("❌ You don't have the rights, lil bro.")
        return

    sent_count = 0
    failed_count = 0

    from discord import TextChannel

    for channel_id in channel_ids_list:
        try:
            channel = await bot.fetch_channel(int(channel_id))
            if isinstance(channel, TextChannel):
                await channel.send(message)
                sent_count += 1
            else:
                failed_count += 1
        except Exception as e:
            failed_count += 1

    await interaction.followup.send(
        f"✅ Sent message to **{sent_count}** channel(s).\n"
        f"❌ Failed for **{failed_count}** channel(s)."
    )

bot.run(bot_key)
