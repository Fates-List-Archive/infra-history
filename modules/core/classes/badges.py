from typing import List, Optional
from modules.core.permissions import is_staff
from modules.core.logger import logger
import modules.models.enums as enums
from discord import Member
import orjson
from config import special_badges

class Badge():
    """Handle badges"""
    @staticmethod
    def from_user(member: discord.Member, badges: Optional[List[str]] = [], bots: list):
        """Make badges from a user given the member, badges and bots"""
        user_flags = {}
        
        # Get core information
        states = [bot["state"] for bot in bots]
        user_flags["certified"] = enums.BotState.certified in states
        user_flags["bot_dev"] = enums.BotState.certified in states or enums.BotState.approved in states
        
        badges = badges if badges else []

        # A discord.Member is part of the support server
        if isinstance(user_dpy, discord.Member):
            user_flags["staff"] = is_staff(staff_roles, user_dpy.roles, 2)[0]
            user_flags["support_server_member"] = True
        
        all_badges = {}
        for badge in badges: # Add in user created badges from blist
            try:
                badge_data = orjson.loads(badge)
            except:
                logger.warning("Failed to open user badge")
                continue
                
            all_badges[badge_data["id"]] = {
                "name": badge_data["name"], 
                "description": badge_data["description"], 
                "image": badge_data["image"]
            }
    
    # Special staff + certified badges (if present)
    for badge_id, badge_data in special_badges.items():
        for key in ("staff", "certified", "bot_dev", "support_server_member"):
            # Check if user is allowed to get badge and if so, give it
            if badge_data.get(key) and user_flags.get(key):
                all_badges[badge_id] = badge_data
            
        if badge_data.get("everyone"):
            all_badges[badge_id] = badge_data
            
    return all_badges