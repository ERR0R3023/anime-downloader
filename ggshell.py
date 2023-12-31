#!/usr/bin/env python3
import cmd
import sys
import os
import subprocess
import re

from requests.exceptions import ConnectionError, ConnectTimeout

import commands
import utils
import config
import outputs
from debug_shell import DebugShell


class GGshell(cmd.Cmd):
    # These are overriden from cmd.Cmd
    # ANSII scapes for orage bg
    prompt = "\x1b[43mGanime >>\x1b[0m"
    # to have '-' character in my commands
    identchars = cmd.Cmd.identchars + '-'
    ruler = '-'
    misc_header = 'Other Help Topics'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.in_cmdloop = False

    def onecmd(self, ind):
        if ind == 'EOF':
            outputs.normal_info()
            return
        try:
            return super().onecmd(ind)
        except (SystemExit, KeyboardInterrupt):
            outputs.normal_info()
        except (ConnectionError, ConnectTimeout):
            outputs.error_info('Slow or no Internet connection. Try again.')

    def cmdloop(self, intro=None):
        """Repeatedly issue a prompt, accept input, parse an initial prefix
off the received input, and dispatch to action methods, passing them
the remainder of the line as argument.

        """

        self.in_cmdloop = True
        self.preloop()
        if self.use_rawinput and self.completekey:
            try:
                import readline
                self.old_completer = readline.get_completer()
                readline.set_completer(self.complete)
                readline.parse_and_bind(self.completekey + ": complete")
            except ImportError:
                pass
        try:
            if intro is not None:
                self.intro = intro
            if self.intro:
                self.stdout.write(str(self.intro) + "\n")
            stop = None
            while not stop:
                if self.cmdqueue:
                    line = self.cmdqueue.pop(0)
                else:
                    try:
                        if self.use_rawinput:
                            try:
                                line = input(self.prompt)
                            except EOFError:
                                line = 'EOF'
                        else:
                            self.stdout.write(self.prompt)
                            self.stdout.flush()
                            line = self.stdin.readline()
                            if not len(line):
                                line = 'EOF'
                            else:
                                line = line.rstrip('\r\n')
                    except KeyboardInterrupt:
                        self.stdout.write('\n^C\n')
                        continue
                line = self.precmd(line)
                stop = self.onecmd(line)
                stop = self.postcmd(stop, line)
            self.postloop()
        finally:
            if self.use_rawinput and self.completekey:
                try:
                    import readline
                    readline.set_completer(self.old_completer)
                except ImportError:
                    pass
        self.in_cmdloop = False

    def preloop(self):
        try:
            import readline
            readline.clear_history()
            if os.path.exists(config.historyfile):
                readline.read_history_file(config.historyfile)
            self.old_completers = readline.get_completer_delims()
            readline.set_completer_delims(
                re.sub(r'-|:|/', '', self.old_completers))
        except ImportError:
            pass

    def postloop(self):
        try:
            import readline
            readline.set_history_length(1000)
            readline.write_history_file(config.historyfile)
            readline.set_completer_delims(self.old_completers)
        except ImportError:
            pass

    def emptyline(self):
        pass

    def completedefault(self, text, line, start, end):
        if re.match(r'([a-z-]+ +){2,}', line):
            return []
        lists = set(utils.read_log().keys()).union(
            set(utils.read_cache(complete=True)))
        match = filter(lambda t: t.startswith(text), lists)
        return utils.completion_list(match)

    def do_help(self, topic):
        if len(topic) == 0:
            import __init__
            outputs.normal_info(__init__.__doc__)
        super().do_help(topic)

    # From here my commands start

    def do_exit(self, inp):
        """Exit this interactive shell."""
        return True

    def do_debug(self, inp):
        """Launch the debug shell.

You can tweak the config variables and other functions without having
to edit the config.py and reloading the app and so on. Use this to see
the effect of configurations which won't be saved.

        """
        if self.in_cmdloop:
            self.postloop()
            DebugShell(self).cmdloop(
                "Debug Shell for Ganime shell.\n" +
                "try `dir()` to see available context variables. " +
                "This shell is same as python shell but has" +
                " Ganime context.")
            self.preloop()
        else:
            DebugShell(self).cmdloop()

    def do_history(self, inp):
        """show the history of the commands.
        """
        if not self.in_cmdloop:
            for j, h in enumerate(open(config.historyfile), start=1):
                h = h.strip()
                if re.match(inp, h):
                    outputs.normal_info(f'{j:3d}:  {h}')
            return
        try:
            import readline
            for j in range(1, readline.get_current_history_length() + 1):
                h = readline.get_history_item(j)
                if re.match(inp, h):
                    outputs.normal_info(f'{j:3d}:  {h}')
        except ImportError:
            pass

    def do_shell(self, inp):
        """Execute shell commands
        """
        subprocess.call(inp, shell=True)

    def do_quality(self, inp):
        """Sets the quality for the anime.
        """
        commands.set_quality(inp)

    def complete_quality(self, text, *ignored):
        possibilities = ['360p', '480p', '720p', '1080p']
        match = filter(lambda t: t.startswith(text), possibilities)
        return list(match)

    def do_geometry(self, inp):
        """Sets the geometry for the external player.
        """
        commands.set_geometry(inp)

    def complete_geometry(self, *ignored):
        return utils.completion_list([config.geometry])

    def do_canon(self, inp):
        """Available list of Canon Episodes.
        """
        commands.check_canon(inp.split())

    def do_fullscreen(self, inp):
        """Toggles the fullscreen setting for external player.
        """
        commands.toggle_fullscreen(inp)

    def complete_fullscreen(self, text, *ignored):
        possibilities = ['yes', 'no', 'on', 'off']
        match = filter(lambda t: t.startswith(text), possibilities)
        return utils.completion_list(match)

    def do_unlog(self, inp):
        """Remove the log entry for the given anime.

USAGE: unlog [ANIME-NAME]
        ANIME-NAME     : Name of the anime
        """
        commands.unlog_anime(inp)

    def do_untrack(self, inp):
        """Remove the given anime from the active track list.

USAGE: untrack [ANIME-NAME]
        ANIME-NAME     : Name of the anime
        """
        commands.untrack_anime(inp)

    def complete_untrack(self, text, line, start, end):
        if re.match(r'([a-z-]+ +){2,}', line):
            return []
        lists = utils.read_log(logfile=config.ongoingfile).keys()
        match = filter(lambda t: t.startswith(text), lists)
        return utils.completion_list(match)

    def do_track(self, inp):
        """Put the given anime into the active track list.

USAGE: track [ANIME-NAME] [EPISODES-RANGE]
        ANIME-NAME     : Name of the anime, or choice number; defaults to 0
        EPISODES-RANGE : Range of the episodes, defaults to all
        """
        commands.track_anime(inp.split())

    def do_tracklist(self, inp):
        """Lists all the animes on the track list.

USAGE: tracklist
        """
        commands.list_tracked()

    def do_latest(self, inp):
        """Get the latest updates from the home page.

USAGE: latest
        """
        commands.latest()

    def do_new(self, inp):
        """Get the new animes from the new page.

USAGE: new
        """
        commands.new()

    def do_updates(self, inp):
        """Get the updates for new episode releases.

USAGE: updates [ANIME-NAME]
        ANIME-NAME     : Name of the anime
        """
        commands.get_updates(inp.strip())

    complete_updates = complete_untrack

    def do_notify(self, inp):
        """Get the updates for new episode releases in notification.

USAGE: notify [ANIME-NAME]
        ANIME-NAME     : Name of the anime
        """
        commands.notify_update(inp.strip())

    complete_notify = complete_untrack

    def do_downloadurl(self, inp):
        """Downloads the anime episode from given gogoanime url
USAGE: downloadurl [GOGOANIME-URL]
        GOGOANIME-URL : Url of the episode from gogoanime website.

related commands: download, streamurl
"""
        commands.download_from_url(inp)

    def do_streamurl(self, inp):
        """Streams the anime episode from given gogoanime url
USAGE: streamurl [GOGOANIME-URL]
        GOGOANIME-URL : Url of the episode from gogoanime website.

related commands: play, continue
"""
        commands.stream_from_url(inp)

    def complete_downloadurl(self, text, line, *ignored):
        lists = set(utils.read_log().keys()).union(
            set(utils.read_cache(complete=True)))
        urls = map(lambda name: commands.anime_source_module.get_episode_url(name, ''), lists)
        match = filter(lambda t: t.startswith(text), urls)
        return utils.completion_list(match)

    complete_streamurl = complete_downloadurl

    def do_download(self, inp):
        """Download the anime episodes in given range

USAGE: download [ANIME-NAME] [EPISODES-RANGE]
        ANIME-NAME     : Name of the anime, or choice number; defaults to 0
        EPISODES-RANGE : Range of the episodes, defaults to all

related commands: play, continue, streamurl
        """
        commands.download_anime(inp.split())

    def do_list(self, inp):
        """List the episodes available for the given anime.

USAGE: list [ANIME-NAME] [EPISODES-RANGE]
        ANIME-NAME     : Name of the anime, or choice number; defaults to 0
        EPISODES-RANGE : Range of the episodes, defaults to all

related commands: info, local
        """
        commands.list_episodes(inp.split())

    def do_web(self, inp):
        """Play the given episodes of the given anime in browser.

USAGE: web [ANIME-NAME] [EPISODES-RANGE]
        ANIME-NAME     : Name of the anime, or choice number; defaults to 0
        EPISODES-RANGE : Range of the episodes, defaults to all

related commands: play, continue, webcontinue
        """
        commands.watch_episode_in_web(inp.split())

    def do_webcontinue(self, inp):
        """Continue playing the given anime in browser.

USAGE: webcontinue [ANIME-NAME]
        ANIME-NAME     : Name of the anime, or choice number; defaults to 0
        """
        commands.continue_play(inp.split(),
                               play_func=commands.watch_episode_in_web)

    def do_play(self, inp):
        """Play the given episodes of the given anime.

USAGE: play [ANIME-NAME] [EPISODES-RANGE]
        ANIME-NAME     : Name of the anime, or choice number; defaults to 0
        EPISODES-RANGE : Range of the episodes, defaults to all

related commands: continue, web, streamurl
        """
        commands.play_anime(inp.split())

    def complete_play(self, text, line, *ignored):
        m = re.match(r'[a-z-]+ +([0-9a-z-]+) +', line)
        if m:
            name = m.group(1)
            log = utils.read_log(name)
            if not log:
                return ["1"]
            ep = re.split("[-,]", utils.Log(log).eps)[-1]
            return [str(int(ep) + 1)]
        return self.completedefault(text, line, *ignored)

    complete_web = complete_play
    complete_watched = complete_play

    def do_savelist(self, inp):
        """List the animes saved for watching later. The continue command will
use this list to decide which episode to watch next. Useful for
skipping fillers.

USAGE: savelist

related commands: save, unsave
        """
        commands.list_saved_anime()

    def do_unsave(self, inp):
        """Play the given episodes of the given anime.

USAGE: unsave [ANIME-NAME]
        ANIME-NAME     : Name of the anime

related commands: savelist, save
        """
        commands.unsave_anime(inp.strip())

    def complete_unsave(self, text, line, *ignored):
        return utils.completion_list(filter(lambda x: re.match(text,x), utils.read_log(logfile=config.watchlaterfile).keys()))

    def do_listlocal(self, inp):
        """List the animes available in local storage.

USAGE: listlocal [KEYWORDS]
        KEYWORDS     : Name of the anime, or regex to filter the list.
        """
        commands.list_local_episodes(inp.split())

    do_locallist = do_listlocal

    def complete_listlocal(self, text, line, *ignored):
        animes = utils.get_local_episodes()
        match = filter(lambda t: t.startswith(text), animes.keys())
        return utils.completion_list(match)

    complete_locallist = complete_listlocal

    def do_local(self, inp):
        """Play the given episodes of the given anime from local storage.

USAGE: local [ANIME-NAME] [EPISODES-RANGE]
        ANIME-NAME     : Name of the anime, or choice number; defaults to 0
        EPISODES-RANGE : Range of the episodes, defaults to all
        """
        if inp.strip() == '':
            self.do_listlocal(inp)
            return
        commands.play_local_anime(inp.split())

    def complete_local(self, text, line, *ignored):
        m = re.match(r'local +([0-9a-z-]+) +', line)
        if m:
            name = m.group(1)
            eps = utils.get_local_episodes(name)[name]
            return [utils.compress_range(utils.extract_range(eps))]
        return self.complete_listlocal(text, line, *ignored)

    def do_watched(self, inp):
        """Update the log so that the given anime (& episodes) are deemed
watched.

USAGE: watched [ANIME-NAME] [EPISODES-RANGE]
        ANIME-NAME     : Name of the anime, or choice number; defaults to 0
        EPISODES-RANGE : Range of the episodes, defaults to all
        """
        commands.update_log(inp.split())

    def do_edit(self, inp):
        """Edit the log so that the given anime (& episodes) replace the
previous log information with new.

USAGE: edit [ANIME-NAME] [EPISODES-RANGE]
        ANIME-NAME     : Name of the anime, or choice number; defaults to 0
        EPISODES-RANGE : Range of the episodes, defaults to all
        """
        commands.edit_log(inp.split())

    def do_save(self, inp):
        """Save the anime or episodes to watch later list. `continue` command
will use this list to decide what to play next, great for skipping
filler episodes.

USAGE: save [ANIME-NAME] [EPISODES-RANGE]
        ANIME-NAME     : Name of the anime, or choice number; defaults to 0
        EPISODES-RANGE : Range of the episodes, defaults to all,
          can be copied from the list of episodes in websites like:
          https://www.animefillerlist.com

        """
        commands.save_anime(inp.split(maxsplit=1))

    def do_continue(self, inp):
        """Play the given anime's unwatched episodes from the start.

USAGE: continue [ANIME-NAME]
        ANIME-NAME     : Name of the anime, or choice number; defaults to 0
        """
        commands.continue_play(inp.split())

    def do_search(self, inp):
        """Search the given keywords in the gogoanime anime list.

USAGE: search [KEYWORDS]
        KEYWORDS     : Name of the anime, in english or japanese.
                       You can use this search result as choice number in
                        next command. first choice is 1.
        """
        commands.search_anime(inp.split())

    def do_log(self, inp):
        """Display the log information.
Pass Anime name or keywords to filter the log. (supports python regex)

USAGE: log [KEYWORDS] [NUMBER]
        KEYWORDS     : Name of the anime, or regex to filter the log.
        NUMBER       : Number of log items to be shown.
        """
        commands.anime_log(inp.split())

    def do_info(self, inp):
        """Show the information of the anime, if you have just searched
something, you can see their info to test if that's what you are searching
for.

USAGE: info [ANIME-NAME]
        ANIME-NAME     : Name of the anime, or choice number; defaults to 0
        """
        commands.anime_info(inp.split())

    def do_check(self, inp):
        """Check if the given episodes range are downloaded and available
offline.
Do not use this when simple commands like ls and tree are enough, as it
also checks the file online to make sure extensions match.
        """
        commands.check_anime(inp.split())

    # Aliases
    do_la = do_latest
    do_ls = do_locallist
    # do_co = do_continue
    do_s = do_search
    # do_pl = do_play
    do_q = do_exit


if __name__ == '__main__':
    if len(sys.argv) == 1:
        gshell = GGshell()
        gshell.cmdloop("""Welcome, This is the CLI interactive for gogoanime.
Type help for more.""")
    else:
        GGshell().onecmd(" ".join(sys.argv[1:]))
