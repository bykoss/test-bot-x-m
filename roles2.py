const { Client, GatewayIntentBits, Collection, Events, ActivityType, EmbedBuilder, PermissionFlagsBits, ActionRowBuilder, ButtonBuilder, ButtonStyle, ModalBuilder, TextInputBuilder, TextInputStyle, StringSelectMenuBuilder, ComponentType } = require('discord.js');
const fs = require('fs');
const path = require('path');
const { token } = require('./config.json');

// Crear el cliente del bot
const client = new Client({
    intents: [
        GatewayIntentBits.Guilds,
        GatewayIntentBits.GuildMessages,
        GatewayIntentBits.MessageContent,
        GatewayIntentBits.GuildMembers,
        GatewayIntentBits.GuildMessageReactions,
        GatewayIntentBits.GuildBans,
        GatewayIntentBits.GuildPresences,
        GatewayIntentBits.GuildEmojisAndStickers,
        GatewayIntentBits.GuildIntegrations,
        GatewayIntentBits.GuildWebhooks,
        GatewayIntentBits.GuildInvites,
        GatewayIntentBits.GuildVoiceStates,
        GatewayIntentBits.GuildScheduledEvents
    ]
});

// Colección de comandos
client.commands = new Collection();

// Configuración del antinuke
const antinukeConfig = new Map();
const raidProtection = new Map();
const userActionCounts = new Map();
const warns = new Map(); // Almacenar advertencias
const mutedUsers = new Map(); // Usuarios silenciados
const tempBans = new Map(); // Baneos temporales

// Cargar comandos
const commandsPath = path.join(__dirname, 'commands');
if (!fs.existsSync(commandsPath)) {
    fs.mkdirSync(commandsPath, { recursive: true });
}

// Crear carpetas de comandos si no existen
const commandFolders = ['moderation', 'utility', 'fun', 'antinuke', 'administration', 'information', 'economy', 'music', 'leveling', 'welcome'];
for (const folder of commandFolders) {
    const folderPath = path.join(commandsPath, folder);
    if (!fs.existsSync(folderPath)) {
        fs.mkdirSync(folderPath, { recursive: true });
    }
}

// Función para cargar comandos
function loadCommands() {
    for (const folder of commandFolders) {
        const folderPath = path.join(commandsPath, folder);
        if (fs.existsSync(folderPath)) {
            const commandFiles = fs.readdirSync(folderPath).filter(file => file.endsWith('.js'));
            
            for (const file of commandFiles) {
                const filePath = path.join(folderPath, file);
                try {
                    delete require.cache[require.resolve(filePath)];
                    const command = require(filePath);
                    
                    if ('data' in command && 'execute' in command) {
                        client.commands.set(command.data.name, command);
                        console.log(`[COMANDO CARGADO] \${command.data.name}`);
                    } else {
                        console.log(`[ADVERTENCIA] El comando en \${filePath} falta la propiedad "data" o "execute"`);
                    }
                } catch (error) {
                    console.error(`Error al cargar el comando ${file}:`, error);
                }
            }
        }
    }
}

// Evento de ready
client.once(Events.ClientReady, () => {
    console.log(`¡Bot iniciado como ${client.user.tag}!`);
    
    // Establecer presencia del bot
    client.user.setPresence({
        activities: [{
            name: 'Protegiendo servidores | ,help',
            type: ActivityType.Watching
        }],
        status: 'online'
    });
    
    // Cargar comandos
    loadCommands();
    
    // Registrar comandos slash
    const commands = [];
    client.commands.forEach(command => {
        commands.push(command.data.toJSON());
    });
    
    client.application.commands.set(commands)
        .then(() => console.log('Comandos slash registrados correctamente'))
        .catch(console.error);
});

// Manejar interacciones de comandos slash
client.on(Events.InteractionCreate, async interaction => {
    if (!interaction.isChatInputCommand() && !interaction.isButton() && !interaction.isModalSubmit() && !interaction.isStringSelectMenu()) return;
    
    if (interaction.isButton()) {
        await handleButtonInteraction(interaction);
        return;
    }
    
    if (interaction.isModalSubmit()) {
        await handleModalSubmit(interaction);
        return;
    }
    
    if (interaction.isStringSelectMenu()) {
        await handleSelectMenu(interaction);
        return;
    }
    
    const command = client.commands.get(interaction.commandName);
    
    if (!command) {
        console.error(`No se encontró el comando ${interaction.commandName}`);
        return;
    }
    
    try {
        await command.execute(interaction, client);
    } catch (error) {
        console.error(error);
        const errorMessage = {
            content: 'Hubo un error al ejecutar este comando.',
            ephemeral: true
        };
        
        if (interaction.replied || interaction.deferred) {
            await interaction.followUp(errorMessage);
        } else {
            await interaction.reply(errorMessage);
        }
    }
});

// Función para manejar interacciones de botones
async function handleButtonInteraction(interaction) {
    const [action, userId, guildId] = interaction.customId.split('-');
    
    if (action === 'verify') {
        // Lógica para verificación
        const guild = client.guilds.cache.get(guildId);
        const member = guild.members.cache.get(userId);
        
        if (member) {
            const role = guild.roles.cache.find(r => r.name === 'Verificado');
            if (role) {
                await member.roles.add(role);
                await interaction.update({ content: '¡Verificación completada!', components: [] });
            }
        }
    } else if (action === 'accept') {
        // Lógica para aceptar solicitud
        await interaction.update({ content: 'Solicitud aceptada.', components: [] });
    } else if (action === 'deny') {
        // Lógica para denegar solicitud
        await interaction.update({ content: 'Solicitud denegada.', components: [] });
    }
}

// Función para manejar envíos de modales
async function handleModalSubmit(interaction) {
    const [action] = interaction.customId.split('-');
    
    if (action === 'suggestion') {
        const suggestion = interaction.fields.getTextInputValue('suggestionInput');
        // Lógica para guardar sugerencia
        await interaction.reply({ content: '¡Sugerencia enviada correctamente!', ephemeral: true });
    } else if (action === 'application') {
        // Lógica para procesar aplicación
        await interaction.reply({ content: '¡Aplicación enviada correctamente!', ephemeral: true });
    }
}

// Función para manejar menús de selección
async function handleSelectMenu(interaction) {
    const [action] = interaction.customId.split('-');
    
    if (action === 'role') {
        const selectedRoles = interaction.values;
        // Lógica para asignar roles
        await interaction.reply({ content: `Roles asignados: ${selectedRoles.join(', ')}`, ephemeral: true });
    } else if (action === 'help') {
        const category = interaction.values[0];
        // Lógica para mostrar ayuda de categoría
        await interaction.reply({ content: `Mostrando ayuda para: \${category}`, ephemeral: true });
    }
}

// Sistema de antinuke
client.on(Events.GuildMemberAdd, async member => {
    const guildId = member.guild.id;
    
    // Verificar si la protección antiraid está activada
    if (raidProtection.has(guildId)) {
        const config = raidProtection.get(guildId);
        const now = Date.now();
        
        // Verificar edad de la cuenta
        const accountAge = now - member.user.createdTimestamp;
        const minAge = config.minAccountAge || 7 * 24 * 60 * 60 * 1000; // 7 días por defecto
        
        if (accountAge < minAge) {
            await member.kick('Cuenta demasiado nueva (protección antiraid)');
            console.log(`Miembro expulsado por antiraid: ${member.user.tag} (Cuenta creada hace ${Math.round(accountAge / (24 * 60 * 60 * 1000))} días)`);
            return;
        }
        
        // Verificar si tiene avatar
        if (config.requireAvatar && !member.user.avatarURL()) {
            await member.kick('Sin avatar (protección antiraid)');
            console.log(`Miembro expulsado por antiraid: \${member.user.tag} (Sin avatar)`);
            return;
        }
    }
});

// Sistema de antinuke para acciones de moderación
client.on(Events.GuildBanAdd, async (ban) => {
    await checkAntinukeAction(ban.guild, 'ban', ban.user.id, ban.guild.client.user.id);
});

client.on(Events.GuildMemberRemove, async (member) => {
    // Verificar si fue expulsado
    const fetchedLogs = await member.guild.fetchAuditLogs({
        limit: 1,
        type: 'MEMBER_KICK'
    });
    
    const kickLog = fetchedLogs.entries.first();
    if (kickLog) {
        await checkAntinukeAction(member.guild, 'kick', member.id, kickLog.executor.id);
    }
});

client.on(Events.ChannelCreate, async (channel) => {
    const fetchedLogs = await channel.guild.fetchAuditLogs({
       
