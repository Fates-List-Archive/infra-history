from typing import List, Optional
from modules.core.permissions import is_staff
from modules.core.logger import logger
import modules.models.enums as enums
from discord import Member
import orjson
from config import staff_roles, special_badges
from pydantic import BaseModel

class Badge(BaseModel):
    """Handle badges"""
    id: str
    name: str
    description: str
    image: str
    staff: Optional[bool] = False
    cert_dev: Optional[bool] = False
    bot_dev: Optional[bool] = False
    support_server_member: Optional[bool] = False
    everyone: Optional[bool] = False
    
    @staticmethod
    def from_user(member: Member, badges: Optional[List[str]] = [], bot_dev: Optional[bool] = False, cert_dev: Optional[bool] = False):
        """Make badges from a user given the member, badges and bots"""
        user_flags = {}
        
        user_flags["cert_dev"] = cert_dev
        user_flags["bot_dev"] = bot_dev
        user_flags["everyone"] = True
        
        badges = badges if badges else []

        # A discord.Member is part of the support server
        if isinstance(member, Member):
            user_flags["staff"] = is_staff(staff_roles, member.roles, 2)[0]
            user_flags["discord_member"] = True
        
        all_badges = []
        for badge in badges: # Add in user created badges from blist
            try:
                badge_data = orjson.loads(badge)
            except:
                logger.warning("Failed to open user badge")
                continue
                
            all_badges.append(badge_data)
    
        # Special staff + certified badges (if present)
        for badge in special_badges:
            # Check if user is allowed to get badge and if so, give it
            check = len([key for key in badge["req"] if user_flags.get(key)])
            if check:
                all_badges.append(badge)
            
        return all_badges
