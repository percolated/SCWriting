import re


class Sc:
    def __init__(self, code):
        self.code = code
        self.lines = code.splitlines()
        self.line_nr = 0
        self.log = None

        # Enhanced-language state
        self.character_defs = {}
        self.anim_defs = {}
        self.stage_positions = {}
        self.character_positions = {}
        self.template_defs = {}
        self.event_id = None
        self.voice_seq = 10
        self.auto_voice_mode = False
        self.pending_voice_override = None
        self.current_speaker = None
        self.speaker_frames = {}
        self.active_chars = set()
        self.runtime_char_state = {}

    def raise_error(self, message):
        raise SyntaxError(f'Line {self.line_nr}, {message}')

    def parse_program(self):
        program = []
        i = 0

        def add_statement(stmt):
            self._update_stage_state(stmt)
            program.append(stmt)

        while i < len(self.lines):
            self.line_nr = i + 1
            raw_line = self.lines[i]
            line = raw_line.strip()

            if not line or line.startswith('//'):
                i += 1
                continue

            if line.startswith('#character '):
                i = self._parse_character_block(i)
                continue
            if line.startswith('#anim '):
                i = self._parse_anim_block(i)
                continue
            if line.startswith('#stage '):
                i = self._parse_stage_block(i)
                continue
            if line.startswith('#positions'):
                i = self._parse_positions_block(i)
                continue
            if line.startswith('#template '):
                i = self._parse_template_block(i)
                continue
            if line.startswith('#event '):
                self._parse_event_header(line)
                i += 1
                continue
            if line.startswith('@speaker '):
                speaker = line[len('@speaker '):].strip()
                if not speaker:
                    self.raise_error('missing speaker name')
                self.current_speaker = self._resolve_speaker_alias(speaker)
                i += 1
                continue
            if line == '@choice':
                statements, i = self._parse_choice_block(i)
                program.extend(statements)
                continue

            if line == '"""' or line.endswith('"""'):
                statement, i = self._parse_multiline_dialogue(i)
                add_statement(statement)
                continue

            flow_statement = self._parse_flow_line(line)
            if flow_statement is not None:
                if isinstance(flow_statement, list):
                    for stmt in flow_statement:
                        add_statement(stmt)
                else:
                    add_statement(flow_statement)
                i += 1
                continue

            if self._is_template_invocation(line):
                expanded = self._expand_template_invocation(line)
                self.lines = self.lines[:i] + expanded + self.lines[i + 1:]
                continue

            if line.startswith('@'):
                statement, handled = self._parse_enhanced_function(line)
                if handled:
                    if statement is None:
                        pass
                    elif isinstance(statement, list):
                        for stmt in statement:
                            add_statement(stmt)
                    else:
                        add_statement(statement)
                else:
                    self.raise_error(f'unsupported command syntax: {line}')
                i += 1
                continue

            statement = self._parse_dialogue_line(line)
            add_statement(statement)
            i += 1

        return program

    def interpret(self):
        old_arr = self.parse_program()
        clean_arr = []
        skip_next = False

        # merge consecutive non-breaking items
        for i in range(len(old_arr)):
            if skip_next:
                skip_next = False
                continue

            current = old_arr[i]

            # Check if we should merge with next item
            if i < len(old_arr) - 1:
                next_item = old_arr[i + 1]
                # Merge if current item has no break conditions (waitTime, textFrame with value)
                has_wait = 'waitTime' in current
                has_text_break = 'textFrame' in current and current.get('textFrame') != 'off'
                has_flow_break = (
                    'label' in current
                    or 'nextLabel' in current
                    or 'select' in current
                    or 'label' in next_item
                    or 'nextLabel' in next_item
                    or 'select' in next_item
                )
                # Keep character visibility/effect transitions as standalone tracks.
                # Otherwise sequences like @hide -> @cos may merge and carry fade-out
                # effect onto the new costume entry.
                has_char_effect_break = (
                    'charEffect' in current
                    or 'charEffect' in next_item
                )

                if not has_wait and not has_text_break and not has_flow_break and not has_char_effect_break:
                    # Merge with next item
                    merged = {**current, **next_item}
                    clean_arr.append(merged)
                    skip_next = True
                    continue

            clean_arr.append(current)

        # final check - ensure all items have textFrame
        for item in clean_arr:
            if 'textFrame' not in item and 'select' not in item:
                item['textFrame'] = 'off'

        clean_arr.append({'label': 'end', 'textFrame': 'off'})
        return clean_arr

    def _update_stage_state(self, statement):
        char_label = statement.get('charLabel')
        if not char_label:
            return

        runtime = self.runtime_char_state.setdefault(char_label, {})
        if 'charType' in statement:
            runtime['charType'] = statement.get('charType')
        if 'charId' in statement:
            runtime['charId'] = statement.get('charId')
        if 'charCategory' in statement:
            runtime['charCategory'] = statement.get('charCategory')
        if 'charPosition' in statement:
            runtime['charPosition'] = dict(statement.get('charPosition'))
            self.active_chars.add(char_label)
        if 'charScale' in statement:
            runtime['charScale'] = statement.get('charScale')

        effect = statement.get('charEffect')
        if isinstance(effect, dict):
            effect_type = effect.get('type')
            alpha = effect.get('alpha')
            if effect_type == 'to' and alpha == 0:
                self.active_chars.discard(char_label)
            else:
                self.active_chars.add(char_label)

    def _parse_flow_line(self, line):
        # Ren'Py-like forms:
        #   label start:
        #   jump scene1
        match = re.match(r'^label\s+(.+?)\s*:\s*$', line)
        if match:
            label = match.group(1).strip()
            if not label:
                self.raise_error('empty label name')
            return {'label': label}

        match = re.match(r'^jump\s+(.+?)\s*$', line)
        if match:
            target = match.group(1).strip()
            if not target:
                self.raise_error('empty jump target')
            return {'nextLabel': target}

        # choice "Text A" -> label_a | "Text B" -> label_b | "Text C" -> label_c
        match = re.match(r'^choice\s+(.+)$', line)
        if match:
            return self._parse_choice_entries(match.group(1).strip())

        return None

    def _parse_choice_entries(self, raw):
        # Parse repeated chunks: "text" -> target, separated by '|'
        pattern = re.compile(r'"((?:[^"\\]|\\.)*)"\s*->\s*([^|]+?)(?=\s*\||\s*$)')
        matches = list(pattern.finditer(raw))
        if not matches:
            self.raise_error('invalid choice syntax')

        entries = []
        consumed = ''.join(
            raw[m.start():m.end()] + ('|' if i < len(matches) - 1 else '')
            for i, m in enumerate(matches)
        )
        compact_in = re.sub(r'\s+', '', raw)
        compact_ok = re.sub(r'\s+', '', consumed)
        if compact_in != compact_ok:
            self.raise_error('invalid choice syntax')

        for idx, m in enumerate(matches):
            text = m.group(1).replace('\\r', '\r').replace('\\n', '\n').replace('\\"', '"')
            target = m.group(2).strip()
            if not target:
                self.raise_error('empty choice nextLabel')
            entry = {
                'select': text,
                'nextLabel': target,
            }
            if idx == len(matches) - 1:
                entry['textCtrl'] = 'cm'
            entries.append(entry)
        return entries

    def _parse_choice_block(self, line_index):
        i = line_index + 1
        option_lines = []
        while i < len(self.lines):
            raw = self.lines[i]
            stripped = raw.strip()
            if not stripped:
                break
            if not raw[:1].isspace():
                break
            if stripped.startswith('//'):
                i += 1
                continue
            option_lines.append(stripped)
            i += 1

        if not option_lines:
            self.line_nr = line_index + 1
            self.raise_error('empty @choice block')

        raw = ' | '.join(option_lines)
        return self._parse_choice_entries(raw), i

    def _parse_kv_block(self, start_index):
        data = {}
        i = start_index

        while i < len(self.lines):
            raw = self.lines[i]
            stripped = raw.strip()

            if not stripped:
                break
            if stripped.startswith('//'):
                i += 1
                continue
            if not raw[:1].isspace():
                break
            if ':' not in stripped:
                self.line_nr = i + 1
                self.raise_error('expected key: value in block')

            key, value = stripped.split(':', 1)
            data[key.strip().lower()] = value.strip()
            i += 1

        return data, i

    def _parse_character_block(self, line_index):
        line = self.lines[line_index].strip()
        name = line[len('#character '):].strip()
        if not name:
            self.raise_error('missing character name in #character block')

        self.line_nr = line_index + 1
        data, next_index = self._parse_kv_block(line_index + 1)
        if not data:
            self.raise_error('empty #character block')

        self.character_defs[name] = data
        return next_index

    def _parse_anim_block(self, line_index):
        line = self.lines[line_index].strip()
        name = line[len('#anim '):].strip()
        if not name:
            self.raise_error('missing preset name in #anim block')

        self.line_nr = line_index + 1
        data, next_index = self._parse_kv_block(line_index + 1)
        if not data:
            self.raise_error('empty #anim block')

        mapped = {}
        for key, value in data.items():
            if key == 'main':
                mapped['charAnim1'] = value
            elif key == 'face':
                mapped['charAnim2'] = value
            elif key == 'lip':
                mapped['charLipAnim'] = value
            elif key == 'eye':
                mapped['charAnim4'] = value
            else:
                mapped[key] = value

        self.anim_defs[name] = mapped
        return next_index

    def _parse_stage_block(self, line_index):
        self.line_nr = line_index + 1
        data, next_index = self._parse_kv_block(line_index + 1)
        if not data:
            self.raise_error('empty #stage block')

        for label, coord in data.items():
            self.stage_positions[label] = self._parse_position(coord)

        return next_index

    def _parse_positions_block(self, line_index):
        self.line_nr = line_index + 1
        data, next_index = self._parse_kv_block(line_index + 1)
        if not data:
            self.raise_error('empty #positions block')

        for char_name, pos_hint in data.items():
            self.character_positions[char_name] = pos_hint

        return next_index

    def _parse_template_block(self, line_index):
        line = self.lines[line_index].strip()
        match = re.match(r'^#template\s+([A-Za-z_]\w*)(?:\s+\{([^}]*)\})?\s*$', line)
        if not match:
            self.raise_error('invalid #template header')

        name = match.group(1)
        params_raw = match.group(2) or ''
        params = [x.strip() for x in params_raw.split(',') if x.strip()]

        body = []
        i = line_index + 1
        while i < len(self.lines):
            raw = self.lines[i]
            stripped = raw.strip()
            if not stripped:
                break
            if not raw[:1].isspace():
                break
            if stripped.startswith('//'):
                i += 1
                continue
            body.append(stripped)
            i += 1

        if not body:
            self.raise_error('empty #template block')

        self.template_defs[name] = {'params': params, 'body': body}
        return i

    def _parse_event_header(self, line):
        event_id = line[len('#event '):].strip()
        if not event_id:
            self.raise_error('missing event id')
        self.event_id = event_id
        self.voice_seq = 10

    def _parse_position(self, text):
        match = re.match(r'^\s*(-?\d+)\s*,\s*(-?\d+)\s*,\s*(-?\d+)\s*$', text)
        if not match:
            self.raise_error(f'invalid position: {text}')
        return {
            'x': int(match.group(1)),
            'y': int(match.group(2)),
            'order': int(match.group(3)),
        }

    def _resolve_position(self, char_name, position_hint):
        hint = position_hint
        char_cfg = self.character_defs.get(char_name, {})

        if hint is None:
            hint = char_cfg.get('position') or char_cfg.get('pos')
        if hint is None:
            hint = self.character_positions.get(char_name)

        if hint is None:
            return None

        if hint in self.stage_positions:
            return self.stage_positions[hint]

        return self._parse_position(hint)

    def _next_auto_voice_id(self):
        if not self.event_id:
            self.raise_error('@voice auto requires #event <event_id>')
        voice_id = f'{self.event_id}{self.voice_seq:04d}'
        self.voice_seq += 10
        return voice_id

    def _extract_voice_id(self, voice_path):
        match = re.match(r'^produce_events/(\d+)/(\d+)$', voice_path)
        if not match:
            return None
        return int(match.group(2))

    def _sync_voice_sequence(self, voice_id_str):
        if not self.event_id:
            return
        if not voice_id_str.startswith(self.event_id):
            return
        tail = voice_id_str[len(self.event_id):]
        if not tail.isdigit():
            return
        next_seq = int(tail) + 10
        if next_seq > self.voice_seq:
            self.voice_seq = next_seq

    def _resolve_voice(self, voice_arg):
        voice = voice_arg.strip()

        if voice in ('auto', 'id:auto'):
            voice_id = self._next_auto_voice_id()
            return f'produce_events/{self.event_id}/{voice_id}'

        if voice.startswith('id:'):
            raw_id = voice.split(':', 1)[1]
            if not raw_id.isdigit():
                self.raise_error(f'invalid voice id syntax: {voice}')
            if not self.event_id:
                self.raise_error(f'{voice} requires #event <event_id>')
            self._sync_voice_sequence(raw_id)
            return f'produce_events/{self.event_id}/{raw_id}'

        if voice.startswith('/'):
            resolved = voice.lstrip('/')
            match = re.match(r'^produce_events/(\d+)/(\d+)$', resolved)
            if match:
                self._sync_voice_sequence(match.group(2))
            return resolved

        if '/' in voice:
            match = re.match(r'^produce_events/(\d+)/(\d+)$', voice)
            if match:
                self._sync_voice_sequence(match.group(2))
            return voice

        if self.event_id is not None and voice.isdigit():
            self._sync_voice_sequence(voice)
            return f'produce_events/{self.event_id}/{voice}'

        return voice

    def _parse_anim_expr(self, expr):
        result = {}
        for token in [x.strip() for x in expr.split(',') if x.strip()]:
            if token in self.anim_defs:
                for key, value in self.anim_defs[token].items():
                    result[key] = value
                continue
            anim_type = self._get_anim_type(token)
            result[anim_type] = token
        return result

    def _get_anim_type(self, anim):
        if anim.startswith('face_'):
            return 'charAnim2'
        if anim.startswith('lip_'):
            return 'charLipAnim'
        if anim.startswith('eye_'):
            return 'charAnim4'
        return 'charAnim1'

    def _resolve_speaker_alias(self, speaker):
        if speaker in self.character_defs and 'alias' in self.character_defs[speaker]:
            return self.character_defs[speaker]['alias']
        return speaker

    def _speaker_to_char_label(self, speaker):
        # Prefer direct character label match
        if speaker in self.character_defs:
            return speaker

        # Fallback to alias -> character label lookup
        for label, cfg in self.character_defs.items():
            if cfg.get('alias') == speaker:
                return label

        return None

    def _should_emit_char_label(self, char_label):
        if char_label is None:
            return False
        cfg = self.character_defs.get(char_label, {})
        return (
            'type' in cfg
            or 'id' in cfg
            or 'pos' in cfg
            or 'position' in cfg
            or char_label in self.character_positions
        )

    def _default_frame_for_speaker(self, speaker):
        if speaker in self.speaker_frames:
            return self.speaker_frames[speaker]

        if speaker in self.character_defs and 'textframe' in self.character_defs[speaker]:
            return self.character_defs[speaker]['textframe']

        for name, cfg in self.character_defs.items():
            alias = cfg.get('alias')
            if alias == speaker and 'textframe' in cfg:
                return cfg['textframe']

        return '001'

    def _is_auto_voice_skipped_for_char(self, char_label):
        if not char_label:
            return False
        cfg = self.character_defs.get(char_label, {})
        voice_pref = str(cfg.get('voice', '')).strip().lower()
        return voice_pref in ('skip', 'none', 'off', 'mute')

    def _build_dialogue_statement(self, speaker, text, frame=None, anim_expr=None, voice=None):
        if speaker is None:
            self.raise_error('speaker not defined; use @speaker or explicit speaker')

        resolved_speaker = self._resolve_speaker_alias(speaker)
        statement = {
            'speaker': resolved_speaker,
            'text': text.replace('\\r', '\r').replace('\\n', '\n'),
            'textCtrl': 'p',
        }

        if frame:
            statement['textFrame'] = frame
            self.speaker_frames[resolved_speaker] = frame
        else:
            statement['textFrame'] = self._default_frame_for_speaker(resolved_speaker)

        if anim_expr:
            statement.update(self._parse_anim_expr(anim_expr))

        char_label = self._speaker_to_char_label(speaker)
        if not char_label:
            char_label = self._speaker_to_char_label(resolved_speaker)
        should_attach_char = (
            self._should_emit_char_label(char_label)
            and (
                anim_expr is not None
                or char_label in self.active_chars
            )
        )
        if should_attach_char:
            statement['charLabel'] = char_label

        skip_voice = voice in ('skip', 'none', 'off')
        if voice and not skip_voice:
            resolved_voice = self._resolve_voice(voice)
            statement['voice'] = resolved_voice
            voice_id = self._extract_voice_id(resolved_voice)
            if voice_id is not None:
                statement['id'] = voice_id
        else:
            resolved_voice = None
            auto_voice_skip_for_speaker = self._is_auto_voice_skipped_for_char(char_label)
            if skip_voice:
                # Skip this dialogue voice in auto mode while preserving auto mode state.
                # If there is a pending explicit override, consume it for this line.
                if self.pending_voice_override is not None:
                    self.pending_voice_override = None
            elif self.pending_voice_override is not None:
                resolved_voice = self.pending_voice_override
                self.pending_voice_override = None
            elif self.auto_voice_mode and not auto_voice_skip_for_speaker:
                resolved_voice = self._resolve_voice('auto')

            if resolved_voice is not None:
                statement['voice'] = resolved_voice
                voice_id = self._extract_voice_id(resolved_voice)
                if voice_id is not None:
                    statement['id'] = voice_id

        return statement

    def _split_inline_voice(self, line):
        match = re.search(r'(?:^|\s+)@voice\s+(\S+)\s*$', line)
        if match:
            return line[:match.start()].rstrip(), match.group(1)
        return line, None

    def _parse_dialogue_line(self, line):
        line, voice = self._split_inline_voice(line)

        if line.startswith('::'):
            match = re.match(r'^::\s+"([^"]*)"\s*(\d+)?\s*$', line)
            if not match:
                self.raise_error('invalid narration syntax')
            return self._build_dialogue_statement('', match.group(1), match.group(2), voice=voice)

        # [A & B] "text" 001
        match = re.match(r'^\[(.+?)\]\s+"([^"]*)"\s*(\d+)?\s*$', line)
        if match and '&' in match.group(1):
            members = [x.strip() for x in match.group(1).split('&') if x.strip()]
            if len(members) < 2:
                self.raise_error('invalid group dialogue syntax')
            speaker = ' & '.join(members)
            return self._build_dialogue_statement(speaker, match.group(2), match.group(3), voice=voice)

        # [anim] "text" 001 (default speaker required)
        match = re.match(r'^\[([^\]]+)\]\s+"([^"]*)"\s*(\d+)?\s*$', line)
        if match:
            if self.current_speaker is None:
                self.raise_error('missing current speaker for [anim] dialogue')
            return self._build_dialogue_statement(
                self.current_speaker,
                match.group(2),
                match.group(3),
                anim_expr=match.group(1),
                voice=voice,
            )

        # speaker [anim] "text" 001
        match = re.match(r'^(.+?)\s+\[([^\]]+)\]\s+"([^"]*)"\s*(\d+)?\s*$', line)
        if match:
            self.current_speaker = match.group(1).strip()
            return self._build_dialogue_statement(
                match.group(1).strip(),
                match.group(3),
                match.group(4),
                anim_expr=match.group(2),
                voice=voice,
            )

        # speaker "text" 001
        match = re.match(r'^(.+?)\s+"([^"]*)"\s*(\d+)?\s*$', line)
        if match:
            self.current_speaker = match.group(1).strip()
            return self._build_dialogue_statement(
                match.group(1).strip(),
                match.group(2),
                match.group(3),
                voice=voice,
            )

        # "text" 001 (default speaker required)
        match = re.match(r'^"([^"]*)"\s*(\d+)?\s*$', line)
        if match:
            if self.current_speaker is None:
                self.raise_error('missing current speaker; use @speaker')
            return self._build_dialogue_statement(
                self.current_speaker,
                match.group(1),
                match.group(2),
                voice=voice,
            )

        self.raise_error('invalid statement')

    def _parse_multiline_dialogue(self, line_index):
        start = self.lines[line_index].strip()
        anim_expr = None
        if start == '"""':
            speaker = self.current_speaker
        else:
            head = start[:-3].strip()
            # [anim] """ with @speaker context
            match = re.match(r'^\[([^\]]+)\]$', head)
            if match:
                if self.current_speaker is None:
                    self.raise_error('missing current speaker for [anim] multi-line dialogue')
                speaker = self.current_speaker
                anim_expr = match.group(1)
            else:
                # speaker [anim] """
                match = re.match(r'^(.+?)\s+\[([^\]]+)\]$', head)
                if match:
                    self.current_speaker = match.group(1).strip()
                    speaker = match.group(1).strip()
                    anim_expr = match.group(2)
                else:
                    # speaker """
                    if head:
                        self.current_speaker = head
                    speaker = head if head else self.current_speaker

        if speaker is None:
            self.raise_error('missing current speaker for multi-line dialogue')

        text_lines = []
        i = line_index + 1

        while i < len(self.lines):
            current = self.lines[i].rstrip()
            stripped = current.strip()

            if stripped.startswith('"""'):
                trailer = stripped[3:].strip()
                frame = None
                voice = None
                if trailer:
                    end_line, voice = self._split_inline_voice(trailer)
                    end_line = end_line.strip()
                    if end_line:
                        if re.match(r'^\d+$', end_line):
                            frame = end_line
                        else:
                            self.line_nr = i + 1
                            self.raise_error('invalid multi-line dialogue trailer')

                statement = self._build_dialogue_statement(
                    speaker,
                    '\r\n'.join(text_lines),
                    frame,
                    anim_expr=anim_expr,
                    voice=voice,
                )
                return statement, i + 1

            text_lines.append(stripped)
            i += 1

        self.raise_error('unterminated multi-line dialogue block')

    def _parse_enhanced_function(self, line):
        # @choice "Text A" -> label_a | "Text B" -> label_b
        match = re.match(r'^@choice\s+(.+)$', line)
        if match:
            return self._parse_choice_entries(match.group(1).strip()), True

        # @label <name>  /  @label <name>:
        match = re.match(r'^@label\s+(.+?)\s*:?\s*$', line)
        if match:
            label = match.group(1).strip()
            if not label:
                self.raise_error('empty label name')
            return {'label': label}, True

        # @jump <name>
        match = re.match(r'^@jump\s+(.+?)\s*$', line)
        if match:
            target = match.group(1).strip()
            if not target:
                self.raise_error('empty jump target')
            return {'nextLabel': target}, True

        # @bg <name> [effect] [time]
        match = re.match(r'^@bg\s+(\S+)(?:\s+(\S+))?(?:\s+(\d+))?\s*$', line)
        if match:
            bg_name = match.group(1)
            if bg_name.lower() == 'none':
                bg_name = 'off'
            statement = {'bg': bg_name}
            if match.group(2):
                statement['bgEffect'] = match.group(2)
            if match.group(3):
                statement['bgEffectTime'] = int(match.group(3))
            return statement, True

        # @fg <name> [effect] [time]
        match = re.match(r'^@fg\s+(\S+)(?:\s+(\S+))?(?:\s+(\d+))?\s*$', line)
        if match:
            fg_name = match.group(1)
            if fg_name.lower() == 'none':
                fg_name = 'off'
            statement = {'fg': fg_name}
            if match.group(2):
                statement['fgEffect'] = match.group(2)
            if match.group(3):
                statement['fgEffectTime'] = int(match.group(3))
            return statement, True

        # @bgm <name>
        match = re.match(r'^@bgm\s+(\S+)\s*$', line)
        if match:
            return {'bgm': match.group(1)}, True

        # @se <name>
        match = re.match(r'^@se\s+(\S+)\s*$', line)
        if match:
            return {'se': match.group(1)}, True

        # @wait <time_ms>
        match = re.match(r'^@wait\s+(\d+)\s*$', line)
        if match:
            return {'waitType': 'time', 'waitTime': int(match.group(1))}, True

        # @voice shorthand with event expansion
        match = re.match(r'^@voice\s+(\S+)\s*$', line)
        if match:
            voice_arg = match.group(1)
            if voice_arg in ('auto', 'id:auto'):
                self.auto_voice_mode = True
                self.pending_voice_override = None
                return None, True

            resolved_voice = self._resolve_voice(voice_arg)
            self.auto_voice_mode = False
            self.pending_voice_override = resolved_voice
            return None, True

        # @hide char [optional anims] [optional fade_ms]
        # Also supports @hide char <fade_ms> [anims]
        if line.startswith('@hide '):
            rest = line[len('@hide '):].strip()
            fade_ms = 100
            anim_expr = None

            time_match = re.search(r'\s+(\d+)\s*$', rest)
            if time_match:
                fade_ms = int(time_match.group(1))
                rest = rest[:time_match.start()].strip()

            anim_match = re.search(r'\[([^\]]+)\]\s*$', rest)
            if anim_match:
                anim_expr = anim_match.group(1)
                rest = rest[:anim_match.start()].strip()

            time_match = re.search(r'\s+(\d+)\s*$', rest)
            if time_match:
                fade_ms = int(time_match.group(1))
                rest = rest[:time_match.start()].strip()

            parts = [x for x in rest.split() if x]
            if len(parts) == 1:
                char_name = parts[0]
                statement = {
                    'charLabel': char_name,
                    'charEffect': {'type': 'to', 'alpha': 0, 'time': fade_ms},
                }
                if anim_expr:
                    statement.update(self._parse_anim_expr(anim_expr))
                return statement, True

        # @char char [preset or anim list]
        match = re.match(r'^@char\s+(\S+)\s+\[([^\]]+)\]\s*$', line)
        if match:
            statement = {'charLabel': match.group(1)}
            statement.update(self._parse_anim_expr(match.group(2)))
            return statement, True

        # @cos <char> <type> <id> [category]
        match = re.match(r'^@cos\s+(\S+)\s+(\S+)\s+(\S+)(?:\s+(\S+))?\s*$', line)
        if match:
            char_name = match.group(1)
            statement = {
                'charLabel': char_name,
                'charType': match.group(2),
                'charId': match.group(3),
            }
            if match.group(4):
                statement['charCategory'] = match.group(4)

            # Keep costume switches compatible with old EventViewer by
            # emitting current/default position when @cos omits it.
            runtime = self.runtime_char_state.get(char_name, {})
            runtime_position = runtime.get('charPosition')
            if runtime_position is not None:
                statement['charPosition'] = dict(runtime_position)
            else:
                fallback_position = self._resolve_position(char_name, None)
                if fallback_position is not None:
                    statement['charPosition'] = dict(fallback_position)
            if 'charScale' in runtime:
                statement['charScale'] = runtime['charScale']

            return statement, True

        # @show char [position] [anims] [optional fade_ms]
        # Also supports @show char [position] <fade_ms> [anims]
        if line.startswith('@show '):
            rest = line[len('@show '):].strip()
            anim_expr = None
            fade_ms = 100

            time_match = re.search(r'\s+(\d+)\s*$', rest)
            if time_match:
                fade_ms = int(time_match.group(1))
                rest = rest[:time_match.start()].strip()

            anim_match = re.search(r'\[([^\]]+)\]\s*$', rest)
            if anim_match:
                anim_expr = anim_match.group(1)
                rest = rest[:anim_match.start()].strip()

            time_match = re.search(r'\s+(\d+)\s*$', rest)
            if time_match:
                fade_ms = int(time_match.group(1))
                rest = rest[:time_match.start()].strip()

            pos_tuple = None
            pos_match = re.search(r'\(([^)]*)\)\s*$', rest)
            if pos_match:
                pos_tuple = pos_match.group(1).strip()
                rest = rest[:pos_match.start()].strip()

            parts = [x for x in rest.split() if x]
            if parts:
                char_name = parts[0]
                pos_hint = parts[1] if len(parts) > 1 else None
                if pos_hint == 'force':
                    pos_hint = None

                if pos_tuple is not None:
                    position = self._parse_position(pos_tuple)
                else:
                    position = self._resolve_position(char_name, pos_hint)
                if position is None:
                    self.raise_error(f'position required for @show {char_name}')

                statement = {
                    'charLabel': char_name,
                    'charPosition': position,
                    'charEffect': {'type': 'from', 'alpha': 0, 'time': fade_ms},
                }

                if anim_expr:
                    statement.update(self._parse_anim_expr(anim_expr))
                else:
                    cfg = self.character_defs.get(char_name, {})
                    default_anim = cfg.get('default_anim')
                    if default_anim:
                        statement.update(self._parse_anim_expr(default_anim.strip('[]')))

                cfg = self.character_defs.get(char_name, {})
                if 'type' in cfg:
                    statement['charType'] = cfg['type']
                if 'id' in cfg:
                    statement['charId'] = cfg['id']
                if 'category' in cfg:
                    statement['charCategory'] = cfg['category']

                return statement, True

        return None, False

    def _is_template_invocation(self, line):
        match = re.match(r'^([A-Za-z_]\w*)\((.*)\)\s*$', line)
        if not match:
            return False
        return match.group(1) in self.template_defs

    def _expand_template_invocation(self, line):
        match = re.match(r'^([A-Za-z_]\w*)\((.*)\)\s*$', line)
        if not match:
            self.raise_error('invalid template invocation')

        name = match.group(1)
        args_raw = match.group(2).strip()
        args = [x.strip() for x in args_raw.split(',') if x.strip()] if args_raw else []
        template = self.template_defs[name]
        params = template['params']

        if params:
            if len(args) != len(params):
                self.raise_error(
                    f'template {name} expects {len(params)} args, got {len(args)}'
                )
            mapping = dict(zip(params, args))
        else:
            mapping = {}
            if len(args) == 1:
                mapping['char'] = args[0]
            elif len(args) > 1:
                self.raise_error(
                    f'template {name} has no declared params, got {len(args)} args'
                )

        expanded = []
        for body_line in template['body']:
            rendered = body_line
            for key, value in mapping.items():
                rendered = rendered.replace(f'{{{key}}}', value)
            expanded.append(rendered)
        return expanded


if __name__ == "__main__":
    import json
    import sys

    # Validate command-line arguments
    if len(sys.argv) < 2:
        print("Usage: python script.py <input_file.sc>")
        sys.exit(1)

    try:
        with open(sys.argv[1], 'rt', encoding='utf-8') as file:
            program = Sc(file.read())
            filename = sys.argv[1].rsplit('.', 1)[0]  # More robust extension removal
            with open(filename + '.json', 'w', encoding='utf-8') as output:
                json.dump(program.interpret(), output, indent=2, ensure_ascii=False, sort_keys=True)
            print(f"Successfully generated {filename}.json")
    except FileNotFoundError:
        print(f"Error: File '{sys.argv[1]}' not found.")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
